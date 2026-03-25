from datetime import datetime, timezone

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.ports.domain_age_lookup import DomainAgeLookupPort
from app.application.ports.html_fetcher import HtmlFetcherPort
from app.application.ports.tls_validator import TlsValidationResult, TlsValidatorPort
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.domain.enums.risk_level import RiskLevel
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId


class FakeRepository(VerificationRepository):
    def save(self, verification):
        return verification

    def get_by_id(self, verification_id):
        return None

    def list(self, limit: int = 50, offset: int = 0, status=None):
        return []


class FakeIdGenerator(IdGeneratorPort):
    def next_verification_id(self) -> VerificationId:
        return VerificationId.from_string("550e8400-e29b-41d4-a716-446655440000")


class NullDomainAgeLookup(DomainAgeLookupPort):
    def lookup(self, domain: str):
        return None


class NullHtmlFetcher(HtmlFetcherPort):
    def fetch(self, url: str):
        return None


class ValidTlsValidator(TlsValidatorPort):
    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        return TlsValidationResult(is_valid=True, provider_name="stub-tls")


def _build_use_case() -> CreateURLVerificationUseCase:
    return CreateURLVerificationUseCase(
        repository=FakeRepository(),
        id_generator=FakeIdGenerator(),
        scoring_service=RiskScoringEngine(),
        signal_analyzer=DeterministicUrlSignalAnalyzer(),
        domain_recency_signal_analyzer=DomainRecencySignalAnalyzer(
            domain_age_lookup=NullDomainAgeLookup(),
            current_time_provider=lambda: datetime(2026, 3, 17, tzinfo=timezone.utc),
        ),
        html_fetcher=NullHtmlFetcher(),
        html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        transport_security_signal_analyzer=TransportSecuritySignalAnalyzer(
            tls_validator=ValidTlsValidator()
        ),
    )


def test_manual_corpus_calibration_suspicious_urls_score_as_suspicious_or_worse() -> None:
    use_case = _build_use_case()
    suspicious_urls = (
        "http://paypal-login-security-check.example.xyz/verify?redirect=https://example.org",
        "https://microsoft-verify-account.example.top/login",
        "https://outlook.office365.mailbox-auth.example.click/reset",
        "http://192.168.10.24/secure-login",
        "https://appleid-confirm-billing.example.info/signin",
    )

    for url in suspicious_urls:
        result = use_case.execute(CreateVerificationCommand(url=url))
        assert result.risk_assessment is not None
        assert result.risk_assessment.risk_level in {
            RiskLevel.MEDIUM.value,
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        }


def test_manual_corpus_calibration_benign_urls_remain_safe() -> None:
    use_case = _build_use_case()
    benign_urls = (
        "https://verifiko.es/",
        "https://docs.python.org/3/library/urllib.parse.html",
        "https://openai.com/research/",
        "https://github.com/openai/openai-python",
        "https://developer.mozilla.org/en-US/docs/Web/HTTP",
    )

    for url in benign_urls:
        result = use_case.execute(CreateVerificationCommand(url=url))
        assert result.risk_assessment is not None
        assert result.risk_assessment.risk_level == RiskLevel.SAFE.value


def test_manual_corpus_calibration_reduces_known_false_positive_patterns() -> None:
    use_case = _build_use_case()

    accounts_result = use_case.execute(
        CreateVerificationCommand(url="https://accounts.example.org/login")
    )
    assert {signal.signal_type for signal in accounts_result.signals} == {"phishing_keywords"}

    portal_result = use_case.execute(
        CreateVerificationCommand(url="https://customer-portal.example.com/")
    )
    assert all(signal.signal_type != "high_domain_entropy" for signal in portal_result.signals)
