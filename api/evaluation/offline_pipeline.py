from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.application.commands.create_verification_command import CreateVerificationCommand
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
from evaluation.corpus import CorpusSample

_FROZEN_NOW = datetime(2026, 7, 23, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ClassifiedResult:
    """The detection outcome for one sample, reduced to what metrics need."""

    risk_level: str
    score: float
    verdict: str
    terminal_override: bool
    signal_types: tuple[str, ...]
    analysis_warnings: tuple[str, ...]


class _EphemeralRepository(VerificationRepository):
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


class _NullHtmlFetcher(HtmlFetcherPort):
    def fetch(self, url: str, *, user_agent: str | None = None):
        return None


class _StaticHtmlFetcher(HtmlFetcherPort):
    def __init__(self, content: str) -> None:
        self._content = content

    def fetch(self, url: str, *, user_agent: str | None = None):
        return FetchedHtmlDocument(content=self._content, source_url=url, content_type="text/html")


class _ValidTlsValidator(TlsValidatorPort):
    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        return TlsValidationResult(is_valid=True, provider_name="stub-tls")


class _NoopRedirectResolver(RedirectResolverPort):
    def resolve(self, url: str) -> RedirectResolution:
        return RedirectResolution(final_url=url, hops=(), provider_name="stub-redirect")


class _ScriptedRedirectResolver(RedirectResolverPort):
    def __init__(self, final_url: str, hops: tuple[RedirectHop, ...]) -> None:
        self._final_url = final_url
        self._hops = hops

    def resolve(self, url: str) -> RedirectResolution:
        return RedirectResolution(
            final_url=self._final_url,
            hops=self._hops,
            provider_name="stub-redirect",
        )


class _NoopReputationLookup(ReputationLookupPort):
    def lookup(self, hostname: str):
        return None


class _NoopInfrastructureLookup(InfrastructureLookupPort):
    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        return InfrastructureProfile(
            queried_host=hostname,
            provider_name="stub-infrastructure",
            resolved_addresses=(ResolvedAddress(ip_address="203.0.113.10"),),
        )


class OfflineDeterministicClassifier:
    """Runs the real verification use case with fully deterministic, offline
    stubs for every network-backed layer.

    Reputation, infrastructure, domain-age and TLS are neutral stubs, so a
    sample's outcome is driven purely by its URL structure plus any redirect or
    HTML context declared on the sample itself. This isolates the deterministic
    detection logic that a regression gate can assert on reproducibly.
    """

    def classify(self, sample: CorpusSample) -> ClassifiedResult:
        use_case = self._build_use_case(sample)
        dto = use_case.execute(CreateVerificationCommand(url=sample.url))
        assessment = dto.risk_assessment
        if assessment is None:
            raise RuntimeError(f"Verification produced no risk assessment for {sample.url!r}")
        return ClassifiedResult(
            risk_level=assessment.risk_level,
            score=assessment.score,
            verdict=assessment.verdict,
            terminal_override=assessment.terminal_override,
            signal_types=tuple(signal.signal_type for signal in dto.signals),
            analysis_warnings=assessment.analysis_warnings,
        )

    def _build_use_case(self, sample: CorpusSample) -> CreateURLVerificationUseCase:
        html_fetcher: HtmlFetcherPort = (
            _StaticHtmlFetcher(sample.html) if sample.html is not None else _NullHtmlFetcher()
        )
        redirect_resolver = self._redirect_resolver(sample)
        return CreateURLVerificationUseCase(
            repository=_EphemeralRepository(),
            id_generator=_FixedIdGenerator(),
            scoring_service=RiskScoringEngine(),
            signal_analyzer=DeterministicUrlSignalAnalyzer(),
            domain_recency_signal_analyzer=DomainRecencySignalAnalyzer(
                domain_age_lookup=_NullDomainAgeLookup(),
                current_time_provider=lambda: _FROZEN_NOW,
            ),
            redirect_signal_analyzer=RedirectSignalAnalyzer(redirect_resolver=redirect_resolver),
            reputation_signal_analyzer=ReputationSignalAnalyzer(
                reputation_lookup=_NoopReputationLookup()
            ),
            infrastructure_signal_analyzer=InfrastructureSignalAnalyzer(
                infrastructure_lookup=_NoopInfrastructureLookup()
            ),
            html_fetcher=html_fetcher,
            resolved_destination_signal_analyzer=ResolvedDestinationSignalAnalyzer(
                url_signal_analyzer=DeterministicUrlSignalAnalyzer(),
                html_fetcher=html_fetcher,
                html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
            ),
            html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
            transport_security_signal_analyzer=TransportSecuritySignalAnalyzer(
                tls_validator=_ValidTlsValidator()
            ),
            public_target_validator=None,
        )

    @staticmethod
    def _redirect_resolver(sample: CorpusSample) -> RedirectResolverPort:
        if not sample.has_redirect_context:
            return _NoopRedirectResolver()
        hops = tuple(
            RedirectHop(
                status_code=step.status_code,
                source_url=step.source_url,
                target_url=step.target_url,
            )
            for step in sample.redirect_hops
        )
        return _ScriptedRedirectResolver(final_url=sample.redirect_final_url or sample.url, hops=hops)
