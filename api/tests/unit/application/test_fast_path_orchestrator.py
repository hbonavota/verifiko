"""Tests for the fail-fast orchestrator in CreateURLVerificationUseCase.

When the URL-only analysis is already decisively malicious, the expensive
network-bound waves must be skipped; otherwise they run as before.
"""

from datetime import UTC, datetime

from app.application.commands.create_verification_command import (
    CreateVerificationCommand,
)
from app.application.ports.domain_age_lookup import DomainAgeLookupPort
from app.application.ports.html_fetcher import FetchedHtmlDocument, HtmlFetcherPort
from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.redirect_resolver import (
    RedirectResolution,
    RedirectResolverPort,
)
from app.application.ports.reputation_lookup import ReputationLookupPort
from app.application.ports.tls_validator import TlsValidationResult, TlsValidatorPort
from app.application.services.domain_recency_signal_analyzer import (
    DomainRecencySignalAnalyzer,
)
from app.application.services.html_credential_signal_analyzer import (
    HtmlCredentialSignalAnalyzer,
)
from app.application.services.infrastructure_signal_analyzer import (
    InfrastructureSignalAnalyzer,
)
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
from app.application.services.resolved_destination_signal_analyzer import (
    ResolvedDestinationSignalAnalyzer,
)
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.application.use_cases.create_url_verification import (
    CreateURLVerificationUseCase,
)
from app.domain.enums.risk_level import RiskLevel
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId

# A URL whose URL-only signals (deceptive brand-in-subdomain, lure keywords)
# already reach a HIGH verdict without any network lookup.
_DECISIVE_MALICIOUS_URL = "https://paypal.com.security-check-login.com/"
_BENIGN_URL = "https://example.com/"


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


class _CountingDomainAge(DomainAgeLookupPort):
    def __init__(self) -> None:
        self.calls = 0

    def lookup(self, domain: str):
        self.calls += 1
        return None


class _CountingHtmlFetcher(HtmlFetcherPort):
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, url: str, *, user_agent: str | None = None):
        self.calls += 1
        return FetchedHtmlDocument(
            content="<html></html>", source_url=url, content_type="text/html"
        )


class _CountingRedirect(RedirectResolverPort):
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, url: str) -> RedirectResolution:
        self.calls += 1
        return RedirectResolution(final_url=url, hops=(), provider_name="stub")


class _CountingReputation(ReputationLookupPort):
    def __init__(self) -> None:
        self.calls = 0

    def lookup(self, hostname: str):
        self.calls += 1
        return None


class _CountingInfrastructure(InfrastructureLookupPort):
    def __init__(self) -> None:
        self.calls = 0

    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        self.calls += 1
        return InfrastructureProfile(
            queried_host=hostname,
            provider_name="stub",
            resolved_addresses=(ResolvedAddress(ip_address="203.0.113.10"),),
        )


class _ValidTls(TlsValidatorPort):
    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        return TlsValidationResult(is_valid=True, provider_name="stub-tls")


def _build(fast_path_enabled: bool):
    domain_age = _CountingDomainAge()
    html_fetcher = _CountingHtmlFetcher()
    redirect = _CountingRedirect()
    reputation = _CountingReputation()
    infrastructure = _CountingInfrastructure()
    spies = {
        "domain_age": domain_age,
        "html": html_fetcher,
        "redirect": redirect,
        "reputation": reputation,
        "infrastructure": infrastructure,
    }
    use_case = CreateURLVerificationUseCase(
        repository=_FakeRepository(),
        id_generator=_FixedIdGenerator(),
        scoring_service=RiskScoringEngine(),
        signal_analyzer=DeterministicUrlSignalAnalyzer(),
        domain_recency_signal_analyzer=DomainRecencySignalAnalyzer(
            domain_age_lookup=domain_age,
            current_time_provider=lambda: datetime(2026, 7, 24, tzinfo=UTC),
        ),
        redirect_signal_analyzer=RedirectSignalAnalyzer(redirect_resolver=redirect),
        reputation_signal_analyzer=ReputationSignalAnalyzer(
            reputation_lookup=reputation
        ),
        infrastructure_signal_analyzer=InfrastructureSignalAnalyzer(
            infrastructure_lookup=infrastructure
        ),
        html_fetcher=html_fetcher,
        resolved_destination_signal_analyzer=ResolvedDestinationSignalAnalyzer(
            url_signal_analyzer=DeterministicUrlSignalAnalyzer(),
            html_fetcher=html_fetcher,
            html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        ),
        html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        transport_security_signal_analyzer=TransportSecuritySignalAnalyzer(
            tls_validator=_ValidTls()
        ),
        public_target_validator=None,
        parallel_analysis_enabled=False,
        fast_path_enabled=fast_path_enabled,
    )
    return use_case, spies


def _network_calls(spies) -> int:
    return sum(spy.calls for spy in spies.values())


def test_fast_path_skips_network_waves_on_decisive_malicious_url() -> None:
    use_case, spies = _build(fast_path_enabled=True)

    dto = use_case.execute(CreateVerificationCommand(url=_DECISIVE_MALICIOUS_URL))

    # No network lookup was performed...
    assert _network_calls(spies) == 0
    # ...yet the verdict is still (at least) suspicious.
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }


def test_fast_path_still_runs_network_waves_on_benign_url() -> None:
    use_case, spies = _build(fast_path_enabled=True)

    use_case.execute(CreateVerificationCommand(url=_BENIGN_URL))

    # Not decisive on the URL alone -> the full pipeline runs.
    assert _network_calls(spies) > 0


def test_disabled_fast_path_always_runs_network_waves() -> None:
    use_case, spies = _build(fast_path_enabled=False)

    use_case.execute(CreateVerificationCommand(url=_DECISIVE_MALICIOUS_URL))

    # With the flag off, behaviour is unchanged: network waves always run.
    assert _network_calls(spies) > 0
