from datetime import datetime, timezone

from app.application.commands.create_verification_command import CreateVerificationCommand, SignalInput
from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
    DomainRegistrationLookupError,
)
from app.application.ports.html_fetcher import FetchedHtmlDocument, HtmlFetchError, HtmlFetcherPort
from app.application.ports.tls_validator import (
    TlsValidationError,
    TlsValidationResult,
    TlsValidatorPort,
)
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
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


def _build_use_case(
    domain_age_lookup: DomainAgeLookupPort | None = None,
    html_fetcher: HtmlFetcherPort | None = None,
    tls_validator: TlsValidatorPort | None = None,
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
        html_fetcher=html_fetcher or FakeHtmlFetcher(),
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
