from datetime import datetime, timezone

from app.application.commands.create_verification_command import CreateVerificationCommand, SignalInput
from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
    DomainRegistrationLookupError,
)
from app.application.ports.html_fetcher import FetchedHtmlDocument, HtmlFetchError, HtmlFetcherPort
from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupError,
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.redirect_resolver import (
    RedirectHop,
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)
from app.application.ports.tls_validator import (
    TlsValidationError,
    TlsValidationResult,
    TlsValidatorPort,
)
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
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
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.domain.entities.verification import Verification
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId


class FakeRepository(VerificationRepository):
    def __init__(self) -> None:
        self._items: list[Verification] = []

    def save(self, verification: Verification) -> Verification:
        self._items.append(verification)
        return verification

    def get_by_id(self, verification_id: VerificationId) -> Verification | None:
        for item in self._items:
            if item.id == verification_id:
                return item
        return None

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        items = self._items
        if status is not None:
            items = [item for item in items if item.status == status]
        return items[offset : offset + limit]


class FakeIdGenerator(IdGeneratorPort):
    def next_verification_id(self) -> VerificationId:
        return VerificationId.from_string("550e8400-e29b-41d4-a716-446655440000")


class FakeDomainAgeLookup(DomainAgeLookupPort):
    def __init__(self, result: DomainRegistrationInfo | None = None, fail: bool = False) -> None:
        self._result = result
        self._fail = fail

    def lookup(self, domain: str) -> DomainRegistrationInfo | None:
        if self._fail:
            raise DomainRegistrationLookupError(f"lookup failed for {domain}")
        return self._result


class FakeHtmlFetcher(HtmlFetcherPort):
    def __init__(self, document: FetchedHtmlDocument | None = None, fail: bool = False) -> None:
        self._document = document
        self._fail = fail

    def fetch(self, url: str) -> FetchedHtmlDocument | None:
        if self._fail:
            raise HtmlFetchError(f"fetch failed for {url}")
        return self._document


class FakeTlsValidator(TlsValidatorPort):
    def __init__(
        self,
        result: TlsValidationResult | None = None,
        fail: bool = False,
    ) -> None:
        self._result = result or TlsValidationResult(is_valid=True, provider_name="stub-tls")
        self._fail = fail

    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        if self._fail:
            raise TlsValidationError(f"tls validation failed for {hostname}:{port}")
        return self._result


class FakeRedirectResolver(RedirectResolverPort):
    def __init__(
        self,
        result: RedirectResolution | None = None,
        fail: bool = False,
    ) -> None:
        self._result = result or RedirectResolution(
            final_url="https://example.test/",
            hops=(),
            provider_name="stub-redirect",
        )
        self._fail = fail

    def resolve(self, url: str) -> RedirectResolution:
        if self._fail:
            raise RedirectResolutionError(f"redirect resolution failed for {url}")
        return self._result


class FakeReputationLookup(ReputationLookupPort):
    def __init__(
        self,
        matches: dict[str, ReputationMatch] | None = None,
        fail: bool = False,
    ) -> None:
        self._matches = matches or {}
        self._fail = fail

    def lookup(self, hostname: str) -> ReputationMatch | None:
        if self._fail:
            raise ReputationLookupError(f"reputation lookup failed for {hostname}")
        return self._matches.get(hostname)


class FakeInfrastructureLookup(InfrastructureLookupPort):
    def __init__(
        self,
        profile: InfrastructureProfile | None = None,
        fail: bool = False,
    ) -> None:
        self._profile = profile or InfrastructureProfile(
            queried_host="example.test",
            provider_name="stub-infrastructure",
            resolved_addresses=(ResolvedAddress(ip_address="203.0.113.10"),),
        )
        self._fail = fail

    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        if self._fail:
            raise InfrastructureLookupError(f"infrastructure lookup failed for {hostname}:{port}")
        return self._profile


def _build_use_case(
    domain_age_lookup: DomainAgeLookupPort | None = None,
    html_fetcher: HtmlFetcherPort | None = None,
    tls_validator: TlsValidatorPort | None = None,
    redirect_resolver: RedirectResolverPort | None = None,
    reputation_lookup: ReputationLookupPort | None = None,
    infrastructure_lookup: InfrastructureLookupPort | None = None,
) -> CreateURLVerificationUseCase:
    return CreateURLVerificationUseCase(
        repository=FakeRepository(),
        id_generator=FakeIdGenerator(),
        scoring_service=RiskScoringEngine(),
        signal_analyzer=DeterministicUrlSignalAnalyzer(),
        domain_recency_signal_analyzer=DomainRecencySignalAnalyzer(
            domain_age_lookup=domain_age_lookup or FakeDomainAgeLookup(),
            current_time_provider=lambda: datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc),
        ),
        redirect_signal_analyzer=RedirectSignalAnalyzer(
            redirect_resolver=redirect_resolver or FakeRedirectResolver()
        ),
        reputation_signal_analyzer=ReputationSignalAnalyzer(
            reputation_lookup=reputation_lookup or FakeReputationLookup()
        ),
        infrastructure_signal_analyzer=InfrastructureSignalAnalyzer(
            infrastructure_lookup=infrastructure_lookup or FakeInfrastructureLookup()
        ),
        html_fetcher=html_fetcher or FakeHtmlFetcher(),
        resolved_destination_signal_analyzer=ResolvedDestinationSignalAnalyzer(
            url_signal_analyzer=DeterministicUrlSignalAnalyzer(),
            html_fetcher=html_fetcher or FakeHtmlFetcher(),
            html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        ),
        html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        transport_security_signal_analyzer=TransportSecuritySignalAnalyzer(
            tls_validator=tls_validator or FakeTlsValidator()
        ),
    )


def test_create_url_verification_use_case() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(
            url="verifiko.es/login",
            signals=(
                SignalInput(
                    signal_type=SignalType.BRAND_IMPERSONATION,
                    category=SignalCategory.CONTENT_BEHAVIOR,
                    severity=SignalSeverity.HIGH,
                    confidence=92,
                    title="Brand impersonation",
                    description="Brand style copied",
                    source="content-analyzer",
                ),
            ),
        )
    )

    assert dto.id == "550e8400-e29b-41d4-a716-446655440000"
    assert dto.status == "COMPLETED"
    assert dto.risk_assessment is not None
    assert len(dto.signals) >= 1


def test_create_url_verification_use_case_generates_signals_from_url() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(
            url="http://secure-paypal-login.example.xyz/verify?redirect=https://example.org",
        )
    )

    assert dto.risk_assessment is not None
    assert len(dto.signals) >= 2
    assert dto.trace is not None
    assert dto.trace.total_signals == len(dto.signals)
    assert "url-rule-analyzer" in dto.trace.layers_executed
    assert "url-rule-analyzer" in dto.trace.signals_by_source
    assert dto.score_breakdown is not None
    assert dto.score_breakdown.base_score == 100.0
    assert dto.score_breakdown.final_score == dto.risk_assessment.score
    assert dto.risk_assessment.explanation.primary_factors
    assert dto.risk_assessment.analysis_trace
    assert dto.risk_assessment.analysis_trace[0].stage == "url_analysis"


def test_create_url_verification_use_case_adds_recency_signal_for_recent_domain() -> None:
    use_case = _build_use_case(
        FakeDomainAgeLookup(
            DomainRegistrationInfo(
                registered_at=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
                provider_name="stub-rdap",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://fresh-example.test/login"))

    recency_signals = [
        signal for signal in dto.signals if signal.signal_type == "recent_domain_registration"
    ]

    assert len(recency_signals) == 1
    assert "Computed domain age: 2 day(s)." in recency_signals[0].evidence


def test_create_url_verification_use_case_skips_recency_signal_for_old_domain() -> None:
    use_case = _build_use_case(
        FakeDomainAgeLookup(
            DomainRegistrationInfo(
                registered_at=datetime(2025, 12, 1, 9, 0, tzinfo=timezone.utc),
                provider_name="stub-rdap",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://stable-example.test/login"))

    assert all(signal.signal_type != "recent_domain_registration" for signal in dto.signals)


def test_create_url_verification_use_case_continues_when_domain_age_lookup_fails() -> None:
    use_case = _build_use_case(FakeDomainAgeLookup(fail=True))

    dto = use_case.execute(
        CreateVerificationCommand(url="http://secure-paypal-login.example.xyz/verify")
    )

    assert dto.status == "COMPLETED"
    assert dto.risk_assessment is not None
    assert all(signal.signal_type != "recent_domain_registration" for signal in dto.signals)


def test_create_url_verification_use_case_adds_html_login_signal() -> None:
    use_case = _build_use_case(
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Sign in to verify your account</h1>
                    <form action=\"https://collector.bad.example/submit\">
                      <input type=\"email\" name=\"email\" />
                      <input type=\"password\" name=\"password\" />
                      <button type=\"submit\">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/login",
                content_type="text/html; charset=utf-8",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://fresh-example.test/login"))

    assert any(signal.signal_type == "credential_harvest_form" for signal in dto.signals)


def test_create_url_verification_use_case_skips_generic_legitimate_login_surface_signal() -> None:
    use_case = _build_use_case(
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <nav>
                      <a href="/login">Sign in</a>
                      <a href="/signup">Create account</a>
                    </nav>
                    <form action="/session">
                      <input type="email" name="user_email" />
                      <button type="submit">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://github.com",
                content_type="text/html; charset=utf-8",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://github.com"))

    assert all(signal.signal_type != "suspicious_login_interface" for signal in dto.signals)


def test_create_url_verification_use_case_continues_when_html_fetch_fails() -> None:
    use_case = _build_use_case(html_fetcher=FakeHtmlFetcher(fail=True))

    dto = use_case.execute(
        CreateVerificationCommand(url="http://secure-paypal-login.example.xyz/verify")
    )

    assert dto.status == "COMPLETED"
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level != "SAFE"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "fetch failed for http://secure-paypal-login.example.xyz/verify",
    )
    assert dto.trace is not None
    assert "html-credential-analyzer" in dto.trace.layers_executed
    assert any(
        stage.stage == "html_content" and stage.status == "degraded"
        for stage in dto.risk_assessment.analysis_trace
    )


def test_create_url_verification_use_case_adds_insecure_transport_signal_for_http() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="http://portal-example.test/login"))

    assert any(signal.signal_type == "insecure_transport" for signal in dto.signals)


def test_create_url_verification_use_case_adds_tls_validation_failure_signal() -> None:
    use_case = _build_use_case(
        tls_validator=FakeTlsValidator(
            TlsValidationResult(
                is_valid=False,
                provider_name="stub-tls",
                failure_reason="certificate verify failed",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://portal-example.test/login"))

    assert any(signal.signal_type == "tls_validation_failure" for signal in dto.signals)


def test_create_url_verification_use_case_skips_transport_signal_on_valid_https() -> None:
    use_case = _build_use_case(
        tls_validator=FakeTlsValidator(
            TlsValidationResult(
                is_valid=True,
                provider_name="stub-tls",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://portal-example.test/home"))

    assert all(
        signal.signal_type not in {"insecure_transport", "tls_validation_failure"}
        for signal in dto.signals
    )


def test_create_url_verification_use_case_strengthens_deceptive_brand_subdomain() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="https://paypal.com.example.xyz/login"))

    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in dto.signals)
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"HIGH", "CRITICAL"}


def test_create_url_verification_use_case_caps_safe_result_when_coverage_is_degraded() -> None:
    use_case = _build_use_case(html_fetcher=FakeHtmlFetcher(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://openai.com"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 80
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary


def test_create_url_verification_use_case_adds_redirect_signal_for_cross_domain_chain() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/login",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://short.example/r/abc",
                        target_url="https://collector.bad.example/login",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://short.example/r/abc"))

    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)


def test_create_url_verification_use_case_uses_blacklist_match_from_redirect_target() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/login",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link",
                        target_url="https://collector.bad.example/login",
                    ),
                ),
                provider_name="stub-redirect",
            )
        ),
        reputation_lookup=FakeReputationLookup(
            {
                "collector.bad.example": ReputationMatch(
                    queried_value="collector.bad.example",
                    provider_name="stub-feed",
                    confidence=99.0,
                    reference_count=3,
                    match_scope="host",
                    description="Known malicious redirect destination.",
                )
            }
        ),
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link"))

    assert any(signal.signal_type == "blacklist_match" for signal in dto.signals)
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.terminal_override is True
    assert dto.risk_assessment.verdict == "CONFIRMED_MALICIOUS"


def test_create_url_verification_use_case_records_degraded_coverage_when_reputation_is_unavailable() -> None:
    use_case = _build_use_case(reputation_lookup=FakeReputationLookup(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://openai.com"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert "Blacklist reputation intelligence was unavailable for this run." in (
        dto.risk_assessment.summary
    )


def test_create_url_verification_use_case_adds_infrastructure_signal_for_suspicious_ptr() -> None:
    use_case = _build_use_case(
        infrastructure_lookup=FakeInfrastructureLookup(
            InfrastructureProfile(
                queried_host="login.safe-example.test",
                provider_name="stub-infrastructure",
                resolved_addresses=(
                    ResolvedAddress(
                        ip_address="203.0.113.44",
                        reverse_hostname="cust-203-0-113-44.no-ip.org",
                    ),
                ),
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://login.safe-example.test/verify"))

    assert any(signal.signal_type == "suspicious_infrastructure_pattern" for signal in dto.signals)


def test_create_url_verification_use_case_records_degraded_coverage_when_infrastructure_is_unavailable() -> None:
    use_case = _build_use_case(infrastructure_lookup=FakeInfrastructureLookup(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://openai.com"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert "Infrastructure intelligence could not be completed for this run." in (
        dto.risk_assessment.summary
    )


def test_create_url_verification_use_case_analyzes_resolved_destination_url() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://paypal-login-security-check.example.xyz/verify",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/123",
                        target_url="https://paypal-login-security-check.example.xyz/verify",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    destination_signals = [
        signal for signal in dto.signals if signal.source == "resolved-destination-url-analyzer"
    ]

    assert any(signal.signal_type == "brand_impersonation" for signal in destination_signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in destination_signals)


def test_create_url_verification_use_case_analyzes_resolved_destination_html() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/login",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/123",
                        target_url="https://collector.bad.example/login",
                    ),
                ),
                provider_name="stub-redirect",
            )
        ),
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Sign in to verify your account</h1>
                    <form action=\"https://collector.bad.example/submit\">
                      <input type=\"email\" name=\"email\" />
                      <input type=\"password\" name=\"password\" />
                      <button type=\"submit\">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://collector.bad.example/login",
                content_type="text/html; charset=utf-8",
            )
        ),
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert any(
        signal.signal_type == "credential_harvest_form"
        and signal.source == "resolved-destination-html-analyzer"
        for signal in dto.signals
    )
