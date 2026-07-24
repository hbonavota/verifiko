from datetime import datetime, timezone

import pytest

from app.application.commands.create_verification_command import CreateVerificationCommand, SignalInput
from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
    DomainRegistrationLookupError,
)
from app.application.ports.headless_detonation import (
    DetonationForm,
    DetonationResult,
    HeadlessDetonationError,
    HeadlessDetonationPort,
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
from app.application.use_cases.create_url_verification import (
    CreateURLVerificationUseCase,
    _HTML_FETCH_VARIANT_PROFILES,
)
from app.domain.entities.verification import Verification
from app.domain.exceptions.domain_exception import DomainException
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId
from app.infrastructure.external_services.outbound_target_guard import assert_safe_outbound_url


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

    def fetch(
        self,
        url: str,
        *,
        user_agent: str | None = None,
    ) -> FetchedHtmlDocument | None:
        if self._fail:
            raise HtmlFetchError(f"fetch failed for {url}")
        return self._document


class MultiVariantHtmlFetcher(HtmlFetcherPort):
    def __init__(
        self,
        *,
        documents_by_user_agent: dict[str, FetchedHtmlDocument | None],
        failing_user_agents: set[str] | None = None,
    ) -> None:
        self._documents_by_user_agent = documents_by_user_agent
        self._failing_user_agents = failing_user_agents or set()
        self.observed_user_agents: list[str | None] = []

    def fetch(
        self,
        url: str,
        *,
        user_agent: str | None = None,
    ) -> FetchedHtmlDocument | None:
        self.observed_user_agents.append(user_agent)
        if user_agent in self._failing_user_agents:
            raise HtmlFetchError(f"fetch failed for {url}")
        return self._documents_by_user_agent.get(user_agent)


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
    public_target_validator=None,
    headless_detonation=None,
    detonation_enabled: bool = False,
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
        public_target_validator=public_target_validator,
        headless_detonation=headless_detonation,
        detonation_enabled=detonation_enabled,
    )


def _user_agent_for(profile_name: str) -> str:
    return next(profile.user_agent for profile in _HTML_FETCH_VARIANT_PROFILES if profile.name == profile_name)


def _html_document(content: str, source_url: str = "https://fresh-example.test/login") -> FetchedHtmlDocument:
    return FetchedHtmlDocument(
        content=content,
        source_url=source_url,
        content_type="text/html; charset=utf-8",
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
    assert dto.status == "completed"
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

    assert dto.status == "completed"
    assert dto.risk_assessment is not None
    assert all(signal.signal_type != "recent_domain_registration" for signal in dto.signals)


def test_create_url_verification_use_case_keeps_clean_domains_safe_when_domain_age_lookup_fails() -> None:
    use_case = _build_use_case(FakeDomainAgeLookup(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://openai.com"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 100
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.verdict == "TRUSTED"
    assert dto.risk_assessment.analysis_warnings == (
        "Domain registration intelligence was unavailable for this run.",
    )
    assert {signal.signal_type for signal in dto.signals} == {"recognized_reputable_domain"}


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


def test_create_url_verification_use_case_adds_html_challenge_surface_signal() -> None:
    use_case = _build_use_case(
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Security challenge</h1>
                    <p>Approve this verification to continue your account session.</p>
                    <form action="/checkpoint">
                      <input type="text" name="otp_code" />
                      <button type="submit">Approve</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://secure-login.bad-example.test/",
                content_type="text/html; charset=utf-8",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://secure-login.bad-example.test/"))

    assert any(signal.signal_type == "suspicious_login_interface" for signal in dto.signals)


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


def test_create_url_verification_use_case_skips_official_same_site_challenge_surface_signal() -> None:
    use_case = _build_use_case(
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Security challenge</h1>
                    <p>Approve this verification to continue your account session.</p>
                    <form action="/challenge">
                      <input type="text" name="otp_code" />
                      <button type="submit">Approve</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://accounts.google.com/challenge",
                content_type="text/html; charset=utf-8",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://accounts.google.com/challenge"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.verdict == "TRUSTED"
    assert all(
        signal.signal_type not in {"credential_harvest_form", "suspicious_login_interface"}
        for signal in dto.signals
    )


def test_create_url_verification_use_case_continues_when_html_fetch_fails() -> None:
    use_case = _build_use_case(html_fetcher=FakeHtmlFetcher(fail=True))

    dto = use_case.execute(
        CreateVerificationCommand(url="http://secure-paypal-login.example.xyz/verify")
    )

    assert dto.status == "completed"
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level != "SAFE"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "HTML content inspection could not be completed.",
    )
    assert dto.trace is not None
    assert "html-credential-analyzer" in dto.trace.layers_executed
    assert any(
        stage.stage == "html_content" and stage.status == "degraded"
        for stage in dto.risk_assessment.analysis_trace
    )


def test_create_url_verification_use_case_skips_signal_for_equivalent_html_variants() -> None:
    base_desktop = _html_document(
        """
        <html>
          <body>
            <h1>Welcome back</h1>
            <p>Review your account activity to continue.</p>
            <form action="/session" nonce="abc123def456ghi789">
              <input type="email" name="email" />
              <input type="password" name="password" />
              <button type="submit">Sign in</button>
            </form>
            <p>Generated at 2026-04-17T11:15:24Z</p>
          </body>
        </html>
        """,
    )
    mobile_variant = _html_document(
        """
        <html>
          <body>
            <h1>Welcome back</h1>
            <p>Review your account activity to continue.</p>
            <form action="/session" nonce="zyx987wvu654tsr321">
              <input type="email" name="email" />
              <input type="password" name="password" />
              <button type="submit">Sign in</button>
            </form>
            <p>Generated at 2026-04-17T11:16:09Z</p>
          </body>
        </html>
        """,
    )
    googlebot_variant = _html_document(
        """
        <html>
          <body>
            <h1>Welcome back</h1>
            <p>Review your account activity to continue.</p>
            <form action="/session" nonce="ff11ee22dd33cc44bb55aa66">
              <input type="email" name="email" />
              <input type="password" name="password" />
              <button type="submit">Sign in</button>
            </form>
            <p>Generated at 2026-04-17T11:17:41Z</p>
          </body>
        </html>
        """,
    )
    html_fetcher = MultiVariantHtmlFetcher(
        documents_by_user_agent={
            _user_agent_for("desktop"): base_desktop,
            _user_agent_for("mobile"): mobile_variant,
            _user_agent_for("googlebot-like"): googlebot_variant,
        }
    )
    use_case = _build_use_case(html_fetcher=html_fetcher)

    dto = use_case.execute(CreateVerificationCommand(url="https://fresh-example.test/login"))

    assert html_fetcher.observed_user_agents == [
        _user_agent_for("desktop"),
        _user_agent_for("mobile"),
        _user_agent_for("googlebot-like"),
    ]
    assert any(signal.signal_type == "credential_harvest_form" for signal in dto.signals)
    assert not any(signal.signal_type == "content_variation_detected" for signal in dto.signals)


def test_create_url_verification_use_case_adds_content_variation_signal_for_mobile_login_variant() -> None:
    html_fetcher = MultiVariantHtmlFetcher(
        documents_by_user_agent={
            _user_agent_for("desktop"): _html_document(
                """
                <html>
                  <body>
                    <h1>Company updates</h1>
                    <p>Read the latest status bulletin and service notes.</p>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/",
            ),
            _user_agent_for("mobile"): _html_document(
                """
                <html>
                  <body>
                    <h1>Sign in to verify your account</h1>
                    <form action="https://collector.bad.example/submit">
                      <input type="email" name="email" />
                      <input type="password" name="password" />
                      <button type="submit">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
            ),
            _user_agent_for("googlebot-like"): _html_document(
                """
                <html>
                  <body>
                    <h1>Company updates</h1>
                    <p>Read the latest status bulletin and service notes.</p>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/",
            ),
        }
    )
    use_case = _build_use_case(html_fetcher=html_fetcher)

    dto = use_case.execute(CreateVerificationCommand(url="https://fresh-example.test/login"))

    assert any(signal.signal_type == "credential_harvest_form" for signal in dto.signals)
    assert any(signal.signal_type == "content_variation_detected" for signal in dto.signals)


def test_create_url_verification_use_case_adds_content_variation_signal_for_googlebot_gap() -> None:
    login_document = _html_document(
        """
        <html>
          <body>
            <h1>Security challenge</h1>
            <p>Approve this verification to continue your account session.</p>
            <form action="/checkpoint">
              <input type="text" name="otp_code" />
              <button type="submit">Approve</button>
            </form>
          </body>
        </html>
        """,
    )
    html_fetcher = MultiVariantHtmlFetcher(
        documents_by_user_agent={
            _user_agent_for("desktop"): login_document,
            _user_agent_for("mobile"): login_document,
            _user_agent_for("googlebot-like"): _html_document(
                """
                <html>
                  <body>
                    <h1>Welcome</h1>
                    <p>Static documentation landing page.</p>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/",
            ),
        }
    )
    use_case = _build_use_case(html_fetcher=html_fetcher)

    dto = use_case.execute(CreateVerificationCommand(url="https://fresh-example.test/login"))

    assert any(signal.signal_type == "suspicious_login_interface" for signal in dto.signals)
    assert any(signal.signal_type == "content_variation_detected" for signal in dto.signals)


def test_create_url_verification_use_case_records_partial_multi_user_agent_warning_without_degrading_result() -> None:
    baseline_fetcher = MultiVariantHtmlFetcher(
        documents_by_user_agent={
            _user_agent_for("desktop"): _html_document(
                """
                <html>
                  <body>
                    <h1>Company updates</h1>
                    <p>Read the latest status bulletin and service notes.</p>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/",
            ),
            _user_agent_for("mobile"): _html_document(
                """
                <html>
                  <body>
                    <h1>Sign in to verify your account</h1>
                    <form action="https://collector.bad.example/submit">
                      <input type="email" name="email" />
                      <input type="password" name="password" />
                      <button type="submit">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
            ),
            _user_agent_for("googlebot-like"): _html_document(
                """
                <html>
                  <body>
                    <h1>Company updates</h1>
                    <p>Read the latest status bulletin and service notes.</p>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/",
            ),
        }
    )
    degraded_fetcher = MultiVariantHtmlFetcher(
        documents_by_user_agent={
            _user_agent_for("desktop"): _html_document(
                """
                <html>
                  <body>
                    <h1>Company updates</h1>
                    <p>Read the latest status bulletin and service notes.</p>
                  </body>
                </html>
                """,
                source_url="https://fresh-example.test/",
            ),
            _user_agent_for("mobile"): _html_document(
                """
                <html>
                  <body>
                    <h1>Sign in to verify your account</h1>
                    <form action="https://collector.bad.example/submit">
                      <input type="email" name="email" />
                      <input type="password" name="password" />
                      <button type="submit">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
            ),
        },
        failing_user_agents={_user_agent_for("googlebot-like")},
    )
    baseline_use_case = _build_use_case(html_fetcher=baseline_fetcher)
    degraded_use_case = _build_use_case(html_fetcher=degraded_fetcher)

    baseline_dto = baseline_use_case.execute(
        CreateVerificationCommand(url="https://fresh-example.test/login")
    )
    degraded_dto = degraded_use_case.execute(
        CreateVerificationCommand(url="https://fresh-example.test/login")
    )

    assert degraded_dto.status == "completed"
    assert degraded_dto.risk_assessment is not None
    assert baseline_dto.risk_assessment is not None
    assert degraded_dto.risk_assessment.analysis_warnings == (
        "Some user-agent HTML variants could not be fetched, but the analysis continued with the variants that responded.",
    )
    assert degraded_dto.risk_assessment.score == baseline_dto.risk_assessment.score
    assert degraded_dto.risk_assessment.verdict == baseline_dto.risk_assessment.verdict
    assert degraded_dto.risk_assessment.summary == baseline_dto.risk_assessment.summary
    assert any(
        stage.stage == "html_content" and stage.status == "degraded"
        for stage in degraded_dto.risk_assessment.analysis_trace
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

    dto = use_case.execute(
        CreateVerificationCommand(url="https://paypal.com.security-check-login.com/")
    )

    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in dto.signals)
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}


def test_create_url_verification_use_case_strengthens_deceptive_institution_subdomain() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://dgt.gob.es.multa-pendiente.secure-payments.xyz")
    )

    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in dto.signals)
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}


def test_create_url_verification_use_case_strengthens_deep_deceptive_subdomain_chains() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://api.mail.google.com.security.example.net")
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in dto.signals)
    assert any(signal.signal_type == "misleading_subdomain" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_long_deceptive_paypal_subdomain_chains() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(
            url="http://paypal.com.security.check.login.system.update.confirm-account.info/"
        )
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict == "LIKELY_MALICIOUS"
    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in dto.signals)
    assert any(signal.signal_type == "misleading_subdomain" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_suspicious_synthetic_hostname_labels() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="https://secure-verify-9x1k-login.net"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert dto.risk_assessment.score < 81
    assert any(signal.signal_type == "high_domain_entropy" for signal in dto.signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_mailbox_synthetic_hostname_labels() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="https://mailbox-8f2k-review-login.xyz"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "high_domain_entropy" for signal in dto.signals)
    assert any(signal.signal_type == "tactical_email_staging" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_mailbox_mfa_review_lures() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://outlook.office365.mfa-review.mail-access.net/")
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "tactical_email_staging" for signal in dto.signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_mailbox_otp_review_lures() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://outlook.office365.otp-review.mail-access.net/")
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "tactical_email_staging" for signal in dto.signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_mailbox_challenge_review_lures() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://outlook.office365.challenge-review.mail-access.net/")
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "tactical_email_staging" for signal in dto.signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_mailbox_session_review_lures() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://outlook.office365.session-review.mail-access.net/")
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "tactical_email_staging" for signal in dto.signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in dto.signals)


def test_create_url_verification_use_case_caps_safe_result_when_coverage_is_degraded() -> None:
    use_case = _build_use_case(html_fetcher=FakeHtmlFetcher(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://openai.com"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 100
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.verdict == "TRUSTED"
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
    assert dto.risk_assessment.risk_level == "SAFE"
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
    assert dto.risk_assessment.risk_level == "SAFE"
    assert "Infrastructure intelligence could not be completed for this run." in (
        dto.risk_assessment.summary
    )


def test_create_url_verification_use_case_strengthens_static_suspicion_when_domain_age_lookup_fails() -> None:
    use_case = _build_use_case(domain_age_lookup=FakeDomainAgeLookup(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://secure-verify-9x1k-login.net"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 60
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.verdict == "SUSPICIOUS"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert "with medium risk output." in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "Domain registration intelligence was unavailable for this run.",
    )
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_static_suspicion_when_infrastructure_lookup_fails() -> None:
    use_case = _build_use_case(infrastructure_lookup=FakeInfrastructureLookup(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://secure-verify-9x1k-login.net"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 60
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.verdict == "SUSPICIOUS"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert "with medium risk output." in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "Infrastructure intelligence could not be completed for this run.",
    )
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_caps_warning_degraded_result_when_signals_exist() -> None:
    use_case = _build_use_case(html_fetcher=FakeHtmlFetcher(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://g.co/openai"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 80
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert "with low risk output." in dto.risk_assessment.summary
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_source_suspicion_when_redirect_resolution_fails() -> None:
    use_case = _build_use_case(redirect_resolver=FakeRedirectResolver(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/challenge"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 60
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.verdict == "SUSPICIOUS"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert "with medium risk output." in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "Redirect resolution could not be completed for this run.",
    )
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_reauth_source_suspicion_when_redirect_resolution_fails() -> None:
    use_case = _build_use_case(redirect_resolver=FakeRedirectResolver(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/reauth"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 60
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.verdict == "SUSPICIOUS"
    assert dto.risk_assessment.analysis_warnings == (
        "Redirect resolution could not be completed for this run.",
    )
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_keeps_failed_session_shorteners_at_low_caution() -> None:
    use_case = _build_use_case(redirect_resolver=FakeRedirectResolver(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/session"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 80
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert dto.risk_assessment.analysis_warnings == (
        "Redirect resolution could not be completed for this run.",
    )
    assert {signal.signal_type for signal in dto.signals} == {"shortened_url"}


def test_create_url_verification_use_case_keeps_failed_clean_shorteners_at_low_caution() -> None:
    use_case = _build_use_case(redirect_resolver=FakeRedirectResolver(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://g.co/openai"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 80
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert "with low risk output." in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "Redirect resolution could not be completed for this run.",
    )
    assert {signal.signal_type for signal in dto.signals} == {"shortened_url"}


def test_create_url_verification_use_case_strengthens_static_suspicion_when_html_fetch_fails() -> None:
    use_case = _build_use_case(html_fetcher=FakeHtmlFetcher(fail=True))

    dto = use_case.execute(CreateVerificationCommand(url="https://g.co/account/security"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 60
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.verdict == "SUSPICIOUS"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert "with medium risk output." in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "HTML content inspection could not be completed.",
    )
    assert dto.risk_assessment.explanation.coverage_warnings == (
        "HTML content inspection could not be completed.",
    )
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_strengthens_redirected_suspicion_when_destination_fetch_fails() -> None:
    use_case = _build_use_case(
        html_fetcher=FakeHtmlFetcher(fail=True),
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/login",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/out",
                        target_url="https://collector.bad.example/login",
                    ),
                ),
                provider_name="stub-redirect",
            )
        ),
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/out"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.score == 60
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.verdict == "SUSPICIOUS"
    assert "Analysis coverage degraded:" in dto.risk_assessment.summary
    assert "with medium risk output." in dto.risk_assessment.summary
    assert dto.risk_assessment.analysis_warnings == (
        "Resolved destination HTML inspection could not be completed.",
        "HTML content inspection could not be completed.",
    )
    assert dto.risk_assessment.explanation.coverage_warnings == (
        "Resolved destination HTML inspection could not be completed.",
        "HTML content inspection could not be completed.",
    )
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in dto.signals)


def test_create_url_verification_use_case_rejects_unsafe_local_targets() -> None:
    use_case = _build_use_case(public_target_validator=assert_safe_outbound_url)

    try:
        use_case.execute(CreateVerificationCommand(url="https://localhost/login"))
    except DomainException as exc:
        assert str(exc) == "Outbound target is a local or special-use hostname and was blocked."
    else:
        raise AssertionError("Expected unsafe local target to be rejected.")


def test_create_url_verification_use_case_rejects_single_label_targets() -> None:
    use_case = _build_use_case(public_target_validator=assert_safe_outbound_url)

    with pytest.raises(
        DomainException,
        match="Outbound target uses a single-label hostname and was blocked.",
    ):
        use_case.execute(CreateVerificationCommand(url="A"))


def test_create_url_verification_use_case_strengthens_branded_shortener_lures() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="https://g.co/account/security"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert "Compound pattern adjustments applied:" in dto.risk_assessment.summary
    assert "shortened_credential_lure_pattern" not in dto.risk_assessment.summary


def test_create_url_verification_use_case_keeps_clean_shortener_redirects_safe() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://openai.com/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://g.co/openai",
                        target_url="https://openai.com/",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://g.co/openai"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.verdict == "TRUSTED"
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "recognized_reputable_domain" for signal in dto.signals)
    assert all(signal.signal_type != "suspicious_redirect_chain" for signal in dto.signals)
    assert "Compound pattern adjustments applied:" in dto.risk_assessment.summary
    assert "recognized_reputable_domain_bonus" not in dto.risk_assessment.summary


def test_create_url_verification_use_case_flags_shortener_redirects_to_questionable_tlds() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://portal-example.top/landing",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/abcd",
                        target_url="https://portal-example.top/landing",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/abcd"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(signal.signal_type == "questionable_destination_tld" for signal in dto.signals)
    assert any(
        signal.signal_type == "suspicious_redirect_chain"
        and "Final destination uses a questionable TLD: .top." in signal.evidence
        for signal in dto.signals
    )


def test_create_url_verification_use_case_strengthens_redirects_to_thin_questionable_destinations() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://portal-example.top/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/abcd",
                        target_url="https://portal-example.top/",
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
                    <h1>Welcome</h1>
                  </body>
                </html>
                """,
                source_url="https://portal-example.top/",
                content_type="text/html",
            )
        ),
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/abcd"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "MEDIUM"
    assert dto.risk_assessment.score < 55
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(signal.signal_type == "low_information_page" for signal in dto.signals)


@pytest.mark.parametrize("url", ("https://google.com", "https://www.verifiko.es/"))
def test_create_url_verification_use_case_keeps_benign_targets_safe_under_minor_warnings(
    url: str,
) -> None:
    use_case = _build_use_case(
        html_fetcher=FakeHtmlFetcher(fail=True),
        reputation_lookup=FakeReputationLookup(fail=True),
    )

    dto = use_case.execute(CreateVerificationCommand(url=url))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.verdict == "TRUSTED"
    expected_score = 100 if url == "https://google.com" else 98
    assert dto.risk_assessment.score == expected_score
    assert dto.risk_assessment.analysis_warnings


def test_create_url_verification_use_case_surfaces_supporting_trust_context() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="https://openai.com/research"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "SAFE"
    assert "Supporting trust context" in dto.risk_assessment.summary
    assert dto.risk_assessment.explanation is not None
    assert "supported by" in dto.risk_assessment.explanation.headline.lower()
    assert {signal.signal_type for signal in dto.signals} == {"recognized_reputable_domain"}


def test_create_url_verification_use_case_uses_primary_reason_explanation_for_suspicious_urls() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(
        CreateVerificationCommand(url="https://paypal-login-security-check.example.xyz/verify")
    )

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.explanation.headline == (
        "The engine produced a suspicious outcome. Primary concern: "
        "brand or institution impersonation cues."
    )
    assert dto.risk_assessment.explanation.decision_basis.startswith(
        "This result is mainly driven by brand or institution impersonation cues."
    )
    assert "content behavior=" in dto.risk_assessment.explanation.decision_basis
    assert "content_behavior=" not in dto.risk_assessment.explanation.decision_basis


def test_create_url_verification_use_case_does_not_let_reputable_domains_override_risky_signals() -> None:
    use_case = _build_use_case()

    dto = use_case.execute(CreateVerificationCommand(url="http://openai.com:8080/reset"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert any(signal.signal_type == "recognized_reputable_domain" for signal in dto.signals)
    assert any(signal.signal_type == "insecure_transport" for signal in dto.signals)
    assert any(signal.signal_type == "non_standard_port_usage" for signal in dto.signals)
    assert "recognized_reputable_domain_bonus" not in dto.risk_assessment.summary


def test_create_url_verification_use_case_strengthens_shortener_redirected_lures() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://traffic-fine-payment.example.top/notice",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://g.co/pay-now",
                        target_url="https://traffic-fine-payment.example.top/notice",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://g.co/pay-now"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.score < 61
    assert dto.risk_assessment.summary.startswith(
        "Primary concern: brand or institution impersonation cues."
    )
    assert "Additional risk indicators were also detected." in dto.risk_assessment.summary
    assert "Compound pattern adjustments applied:" in dto.risk_assessment.summary
    assert "shortened_redirected_lure_pattern" not in dto.risk_assessment.summary
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(
        signal.signal_type == "brand_impersonation"
        and signal.title == "Institution-style payment or penalty lure"
        for signal in dto.signals
    )


def test_create_url_verification_use_case_strengthens_shortener_redirected_session_lures() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://outlook.office365.session-review.mail-access.net/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/session",
                        target_url="https://outlook.office365.session-review.mail-access.net/",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/session"))
    destination_signals = [
        signal for signal in dto.signals if signal.source == "resolved-destination-url-analyzer"
    ]
    redirect_signals = [signal for signal in dto.signals if signal.source == "redirect-chain-analyzer"]

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict in {"SUSPICIOUS", "LIKELY_MALICIOUS"}
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in redirect_signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in destination_signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in destination_signals)
    assert any(signal.signal_type == "tactical_email_staging" for signal in destination_signals)


def test_create_url_verification_use_case_strengthens_shortener_redirected_reauth_lures() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://google.com.reauth-security-check.user-access.net/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/google-reauth",
                        target_url="https://google.com.reauth-security-check.user-access.net/",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/google-reauth"))
    destination_signals = [
        signal for signal in dto.signals if signal.source == "resolved-destination-url-analyzer"
    ]
    redirect_signals = [
        signal for signal in dto.signals if signal.source == "redirect-chain-analyzer"
    ]

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict == "LIKELY_MALICIOUS"
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in redirect_signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in destination_signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in destination_signals)
    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in destination_signals)


def test_create_url_verification_use_case_strengthens_shortener_redirected_approve_lures() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://google.com.approve-review.user-access.net/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/google-approve",
                        target_url="https://google.com.approve-review.user-access.net/",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/google-approve"))
    destination_signals = [
        signal for signal in dto.signals if signal.source == "resolved-destination-url-analyzer"
    ]
    redirect_signals = [
        signal for signal in dto.signals if signal.source == "redirect-chain-analyzer"
    ]

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"HIGH", "CRITICAL"}
    assert dto.risk_assessment.verdict == "LIKELY_MALICIOUS"
    assert any(signal.signal_type == "shortened_url" for signal in dto.signals)
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in redirect_signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in destination_signals)
    assert any(signal.signal_type == "brand_impersonation" for signal in destination_signals)
    assert any(signal.signal_type == "deceptive_brand_subdomain" for signal in destination_signals)


def test_create_url_verification_use_case_keeps_shortener_redirected_official_challenge_flows_safe() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://accounts.google.com/challenge",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/official-google",
                        target_url="https://accounts.google.com/challenge",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://bit.ly/official-google"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.verdict == "TRUSTED"
    assert {signal.signal_type for signal in dto.signals} == {
        "recognized_reputable_domain",
        "shortened_url",
    }


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

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert any(signal.signal_type == "brand_impersonation" for signal in destination_signals)
    assert any(signal.signal_type == "phishing_keywords" for signal in destination_signals)


def test_create_url_verification_use_case_marks_redirected_login_style_destination_as_caution() -> None:
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
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(
        signal.signal_type == "phishing_keywords"
        and signal.source == "resolved-destination-url-analyzer"
        for signal in dto.signals
    )


def test_create_url_verification_use_case_marks_redirected_reset_destinations_as_caution() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/reset",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/123",
                        target_url="https://collector.bad.example/reset",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(
        signal.signal_type == "phishing_keywords"
        and signal.source == "resolved-destination-url-analyzer"
        for signal in dto.signals
    )


def test_create_url_verification_use_case_marks_redirected_recovery_destinations_as_caution() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/recovery",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/123",
                        target_url="https://collector.bad.example/recovery",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(
        signal.signal_type == "phishing_keywords"
        and signal.source == "resolved-destination-url-analyzer"
        for signal in dto.signals
    )


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


def test_create_url_verification_use_case_analyzes_resolved_destination_challenge_html() -> None:
    class FinalChallengeHtmlFetcher(HtmlFetcherPort):
        def fetch(
            self,
            url: str,
            *,
            user_agent: str | None = None,
        ) -> FetchedHtmlDocument | None:
            if url != "https://collector.bad.example/challenge":
                return None
            return FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Security challenge</h1>
                    <p>Approve this verification to continue your account session.</p>
                    <form action="/checkpoint">
                      <input type="text" name="otp_code" />
                      <button type="submit">Approve</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://collector.bad.example/challenge",
                content_type="text/html; charset=utf-8",
            )

    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/challenge",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/456",
                        target_url="https://collector.bad.example/challenge",
                    ),
                ),
                provider_name="stub-redirect",
            )
        ),
        html_fetcher=FinalChallengeHtmlFetcher(),
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/456"))

    assert any(
        signal.signal_type == "suspicious_login_interface"
        and signal.source == "resolved-destination-html-analyzer"
        for signal in dto.signals
    )


def test_create_url_verification_use_case_skips_benign_redirect_interstitial_html() -> None:
    class FinalOnlyHtmlFetcher(HtmlFetcherPort):
        def fetch(
            self,
            url: str,
            *,
            user_agent: str | None = None,
        ) -> FetchedHtmlDocument | None:
            if url != "https://www.encurtador.dev/redirecionamento/7k3qpqd":
                return None
            return FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Verify redirect</h1>
                    <p>Before continuing, complete this redirect check.</p>
                    <form action="/redirecionamento/7k3qpqd">
                      <input type="password" name="access_code" />
                      <button type="submit">Continue</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://www.encurtador.dev/redirecionamento/7k3qpqd",
                content_type="text/html; charset=utf-8",
            )

    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://www.encurtador.dev/redirecionamento/7k3qpqd",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://sl1nk.com/7k3qpqd",
                        target_url="https://www.encurtador.dev/redirecionamento/7k3qpqd",
                    ),
                ),
                provider_name="stub-redirect",
            )
        ),
        html_fetcher=FinalOnlyHtmlFetcher(),
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://sl1nk.com/7k3qpqd"))

    assert dto.risk_assessment is not None
    assert all(signal.signal_type != "credential_harvest_form" for signal in dto.signals)
    assert all(signal.signal_type != "suspicious_redirect_chain" for signal in dto.signals)
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.trace is not None
    assert dto.trace.total_signals == len(dto.signals) == 0
    assert dto.risk_assessment.summary.startswith("Detected 0 risk signal(s)")


def test_create_url_verification_use_case_keeps_safe_redirect_mismatch_summaries_non_alarmist() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://destination.example/welcome",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/123",
                        target_url="https://destination.example/welcome",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "SAFE"
    assert dto.risk_assessment.summary.startswith("Detected 1 risk signal(s)")
    assert "Primary concern:" not in dto.risk_assessment.summary


def test_create_url_verification_use_case_marks_redirects_to_questionable_tlds_as_caution() -> None:
    use_case = _build_use_case(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://portal-example.top/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://safe.example/link/123",
                        target_url="https://portal-example.top/",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    dto = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert dto.risk_assessment is not None
    assert dto.risk_assessment.risk_level == "LOW"
    assert dto.risk_assessment.verdict == "CAUTION"
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in dto.signals)
    assert any(signal.signal_type == "questionable_destination_tld" for signal in dto.signals)


class RecordingDetonation(HeadlessDetonationPort):
    """Fake headless backend: records the URLs it was asked to detonate and
    returns a canned observation (or raises to exercise the fail-open path)."""

    def __init__(
        self,
        result: DetonationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[str] = []

    def detonate(self, url: str) -> DetonationResult:
        self.calls.append(url)
        if self._error is not None:
            raise self._error
        return self._result or DetonationResult(requested_url=url, final_url=url)


def _offsite_credential_detonation(url: str) -> DetonationResult:
    return DetonationResult(
        requested_url=url,
        final_url=url,
        forms=(
            DetonationForm(has_password_field=True, action_host="harvest.evil-collector.com"),
        ),
    )


def test_async_deep_analysis_folds_behavioral_signals_into_the_verdict() -> None:
    detonation = RecordingDetonation(
        result=_offsite_credential_detonation("https://client-portal.io/")
    )
    use_case = _build_use_case(headless_detonation=detonation, detonation_enabled=True)

    dto = use_case.execute(
        CreateVerificationCommand(url="https://client-portal.io/", deep_analysis=True)
    )

    assert len(detonation.calls) == 1
    assert "client-portal.io" in detonation.calls[0]
    signal_types = {signal.signal_type for signal in dto.signals}
    assert "rendered_credential_form" in signal_types
    assert "offsite_form_action" in signal_types
    assert dto.risk_assessment is not None
    # The behavioral signals fold into the score before it is computed (band
    # escalation/weight calibration is deferred to B.4).
    assert dto.risk_assessment.score < 100
    behavioral_stages = [
        stage
        for stage in dto.risk_assessment.analysis_trace
        if stage.stage == "behavioral_detonation"
    ]
    assert behavioral_stages and behavioral_stages[0].status == "signals_detected"


def test_sync_path_never_detonates_even_when_enabled() -> None:
    detonation = RecordingDetonation()
    use_case = _build_use_case(headless_detonation=detonation, detonation_enabled=True)

    use_case.execute(CreateVerificationCommand(url="https://client-portal.io/"))

    assert detonation.calls == []


def test_detonation_disabled_flag_skips_the_browser() -> None:
    detonation = RecordingDetonation()
    use_case = _build_use_case(headless_detonation=detonation, detonation_enabled=False)

    use_case.execute(
        CreateVerificationCommand(url="https://client-portal.io/", deep_analysis=True)
    )

    assert detonation.calls == []


def test_already_decided_verdict_is_not_detonated() -> None:
    detonation = RecordingDetonation(
        result=_offsite_credential_detonation("https://safe.example/link")
    )
    use_case = _build_use_case(
        headless_detonation=detonation,
        detonation_enabled=True,
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

    dto = use_case.execute(
        CreateVerificationCommand(url="https://safe.example/link", deep_analysis=True)
    )

    assert detonation.calls == []
    assert dto.risk_assessment is not None
    assert dto.risk_assessment.verdict == "CONFIRMED_MALICIOUS"


def test_detonation_failure_is_fail_open() -> None:
    detonation = RecordingDetonation(error=HeadlessDetonationError("browser exploded"))
    use_case = _build_use_case(headless_detonation=detonation, detonation_enabled=True)

    dto = use_case.execute(
        CreateVerificationCommand(url="https://client-portal.io/", deep_analysis=True)
    )

    assert len(detonation.calls) == 1
    assert dto.status == "completed"
    assert all(
        signal.signal_type
        not in {"rendered_credential_form", "offsite_form_action", "drive_by_download"}
        for signal in dto.signals
    )
    assert dto.risk_assessment is not None
    degraded = [
        stage
        for stage in dto.risk_assessment.analysis_trace
        if stage.stage == "behavioral_detonation"
    ]
    assert degraded and degraded[0].status == "degraded"


def test_benign_detonation_result_adds_no_behavioral_signals() -> None:
    detonation = RecordingDetonation()  # default result is benign
    use_case = _build_use_case(headless_detonation=detonation, detonation_enabled=True)

    dto = use_case.execute(
        CreateVerificationCommand(url="https://client-portal.io/", deep_analysis=True)
    )

    assert len(detonation.calls) == 1
    assert all(
        signal.signal_type
        not in {
            "rendered_credential_form",
            "offsite_form_action",
            "js_redirect_to_offsite",
            "drive_by_download",
        }
        for signal in dto.signals
    )
