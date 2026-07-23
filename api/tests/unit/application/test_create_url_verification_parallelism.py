import threading
from datetime import datetime, timezone

import pytest

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.dto.verification_dto import VerificationDTO
from app.application.ports.domain_age_lookup import DomainAgeLookupPort
from app.application.ports.html_fetcher import FetchedHtmlDocument, HtmlFetcherPort
from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.redirect_resolver import (
    RedirectHop,
    RedirectResolution,
    RedirectResolverPort,
)
from app.application.ports.reputation_lookup import ReputationLookupPort
from app.application.ports.tls_validator import TlsValidationResult, TlsValidatorPort
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.infrastructure_signal_analyzer import InfrastructureSignalAnalyzer
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
from app.application.services.resolved_destination_signal_analyzer import (
    ResolvedDestinationSignalAnalyzer,
)
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId

_LOGIN_HTML = (
    "<html><body><h1>Security challenge</h1>"
    "<p>Approve this verification to continue your account session.</p>"
    "<form action=\"/checkpoint\"><input type=\"text\" name=\"otp_code\" />"
    "<button type=\"submit\">Approve</button></form></body></html>"
)


class _FakeRepository(VerificationRepository):
    def save(self, verification):
        return verification

    def get_by_id(self, verification_id):
        return None

    def list(self, limit: int = 50, offset: int = 0, status=None):
        return []


class _FixedIdGenerator(IdGeneratorPort):
    def next_verification_id(self) -> VerificationId:
        return VerificationId.from_string("550e8400-e29b-41d4-a716-446655440000")


class _NullDomainAgeLookup(DomainAgeLookupPort):
    def lookup(self, domain: str):
        return None


class _StaticHtmlFetcher(HtmlFetcherPort):
    def fetch(self, url: str, *, user_agent: str | None = None):
        return FetchedHtmlDocument(content=_LOGIN_HTML, source_url=url, content_type="text/html")


class _ValidTls(TlsValidatorPort):
    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        return TlsValidationResult(is_valid=True, provider_name="stub-tls")


class _ScriptedRedirect(RedirectResolverPort):
    def resolve(self, url: str) -> RedirectResolution:
        final = "https://outlook.office365.session-review.mail-access.net/"
        return RedirectResolution(
            final_url=final,
            hops=(RedirectHop(status_code=302, source_url=url, target_url=final),),
            provider_name="stub-redirect",
        )


class _NoopReputation(ReputationLookupPort):
    def lookup(self, hostname: str):
        return None


class _NoopInfrastructure(InfrastructureLookupPort):
    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        return InfrastructureProfile(
            queried_host=hostname,
            provider_name="stub-infra",
            resolved_addresses=(ResolvedAddress(ip_address="203.0.113.10"),),
        )


def _build_use_case(parallel_analysis_enabled: bool) -> CreateURLVerificationUseCase:
    html_fetcher = _StaticHtmlFetcher()
    return CreateURLVerificationUseCase(
        repository=_FakeRepository(),
        id_generator=_FixedIdGenerator(),
        scoring_service=RiskScoringEngine(),
        signal_analyzer=DeterministicUrlSignalAnalyzer(),
        domain_recency_signal_analyzer=DomainRecencySignalAnalyzer(
            domain_age_lookup=_NullDomainAgeLookup(),
            current_time_provider=lambda: datetime(2026, 7, 23, tzinfo=timezone.utc),
        ),
        redirect_signal_analyzer=RedirectSignalAnalyzer(redirect_resolver=_ScriptedRedirect()),
        reputation_signal_analyzer=ReputationSignalAnalyzer(reputation_lookup=_NoopReputation()),
        infrastructure_signal_analyzer=InfrastructureSignalAnalyzer(
            infrastructure_lookup=_NoopInfrastructure()
        ),
        html_fetcher=html_fetcher,
        resolved_destination_signal_analyzer=ResolvedDestinationSignalAnalyzer(
            url_signal_analyzer=DeterministicUrlSignalAnalyzer(),
            html_fetcher=html_fetcher,
            html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        ),
        html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        transport_security_signal_analyzer=TransportSecuritySignalAnalyzer(tls_validator=_ValidTls()),
        public_target_validator=None,
        parallel_analysis_enabled=parallel_analysis_enabled,
    )


def _durable_view(dto: VerificationDTO) -> dict:
    assessment = dto.risk_assessment
    assert assessment is not None
    return {
        "signals": [
            (
                signal.signal_type,
                signal.category,
                signal.severity,
                signal.confidence,
                signal.detected,
                signal.title,
                signal.description,
                signal.evidence,
                signal.source,
                signal.base_weight,
                signal.tags,
            )
            for signal in dto.signals
        ],
        "score": assessment.score,
        "risk_level": assessment.risk_level,
        "verdict": assessment.verdict,
        "summary": assessment.summary,
        "top_signals": assessment.top_signals,
        "category_breakdown": assessment.category_breakdown,
        "terminal_override": assessment.terminal_override,
        "analysis_warnings": assessment.analysis_warnings,
        "analysis_trace": [
            (stage.stage, stage.source, stage.status, stage.signal_count, stage.signal_titles, stage.warnings)
            for stage in assessment.analysis_trace
        ],
    }


def test_parallel_and_sequential_pipelines_produce_identical_results() -> None:
    command = CreateVerificationCommand(url="https://bit.ly/session-review")

    parallel = _build_use_case(parallel_analysis_enabled=True).execute(command)
    sequential = _build_use_case(parallel_analysis_enabled=False).execute(command)

    assert _durable_view(parallel) == _durable_view(sequential)
    # Sanity: the fixture actually exercises multiple analyzers.
    assert len(parallel.signals) >= 2


def test_run_stage_group_runs_tasks_concurrently() -> None:
    use_case = _build_use_case(parallel_analysis_enabled=True)
    barrier = threading.Barrier(3, timeout=5)

    def make(name: str):
        def task():
            barrier.wait()  # only clears if all three run at the same time
            return name

        return task

    results = use_case._run_stage_group({"a": make("a"), "b": make("b"), "c": make("c")})

    assert results == {"a": "a", "b": "b", "c": "c"}


def test_run_stage_group_falls_back_to_sequential_when_disabled() -> None:
    use_case = _build_use_case(parallel_analysis_enabled=False)
    order: list[str] = []

    def make(name: str):
        def task():
            order.append(name)
            return name

        return task

    results = use_case._run_stage_group({"a": make("a"), "b": make("b")})

    assert results == {"a": "a", "b": "b"}
    assert order == ["a", "b"]  # deterministic, in submission order


def test_run_stage_group_propagates_task_exceptions() -> None:
    use_case = _build_use_case(parallel_analysis_enabled=True)

    class Boom(Exception):
        pass

    def boom():
        raise Boom()

    with pytest.raises(Boom):
        use_case._run_stage_group({"a": lambda: 1, "b": boom})
