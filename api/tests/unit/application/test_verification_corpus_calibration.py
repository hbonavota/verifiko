from datetime import datetime, timezone

import pytest

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.ports.domain_age_lookup import DomainAgeLookupPort
from app.application.ports.html_fetcher import HtmlFetcherPort
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
from app.domain.exceptions.domain_exception import DomainException
from app.domain.enums.risk_level import RiskLevel
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId
from app.infrastructure.external_services.outbound_target_guard import assert_safe_outbound_url


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


class StaticHtmlFetcher(HtmlFetcherPort):
    def __init__(self, content: str) -> None:
        self._content = content

    def fetch(self, url: str):
        from app.application.ports.html_fetcher import FetchedHtmlDocument

        return FetchedHtmlDocument(
            content=self._content,
            source_url=url,
            content_type="text/html",
        )


class ValidTlsValidator(TlsValidatorPort):
    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        return TlsValidationResult(is_valid=True, provider_name="stub-tls")


class NoopRedirectResolver(RedirectResolverPort):
    def resolve(self, url: str) -> RedirectResolution:
        return RedirectResolution(final_url=url, hops=(), provider_name="stub-redirect")


class NoopReputationLookup(ReputationLookupPort):
    def lookup(self, hostname: str):
        return None


class NoopInfrastructureLookup(InfrastructureLookupPort):
    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        return InfrastructureProfile(
            queried_host=hostname,
            provider_name="stub-infrastructure",
            resolved_addresses=(ResolvedAddress(ip_address="203.0.113.10"),),
        )


def _build_use_case(
    public_target_validator=None,
    html_fetcher: HtmlFetcherPort | None = None,
    redirect_resolver: RedirectResolverPort | None = None,
) -> CreateURLVerificationUseCase:
    return CreateURLVerificationUseCase(
        repository=FakeRepository(),
        id_generator=FakeIdGenerator(),
        scoring_service=RiskScoringEngine(),
        signal_analyzer=DeterministicUrlSignalAnalyzer(),
        domain_recency_signal_analyzer=DomainRecencySignalAnalyzer(
            domain_age_lookup=NullDomainAgeLookup(),
            current_time_provider=lambda: datetime(2026, 3, 17, tzinfo=timezone.utc),
        ),
        redirect_signal_analyzer=RedirectSignalAnalyzer(
            redirect_resolver=redirect_resolver or NoopRedirectResolver()
        ),
        reputation_signal_analyzer=ReputationSignalAnalyzer(
            reputation_lookup=NoopReputationLookup()
        ),
        infrastructure_signal_analyzer=InfrastructureSignalAnalyzer(
            infrastructure_lookup=NoopInfrastructureLookup()
        ),
        html_fetcher=html_fetcher or NullHtmlFetcher(),
        resolved_destination_signal_analyzer=ResolvedDestinationSignalAnalyzer(
            url_signal_analyzer=DeterministicUrlSignalAnalyzer(),
            html_fetcher=html_fetcher or NullHtmlFetcher(),
            html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        ),
        html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
        transport_security_signal_analyzer=TransportSecuritySignalAnalyzer(
            tls_validator=ValidTlsValidator()
        ),
        public_target_validator=public_target_validator,
    )


def test_manual_corpus_calibration_suspicious_urls_score_as_suspicious_or_worse() -> None:
    use_case = _build_use_case()
    suspicious_urls = (
        "http://paypal-login-security-check.example.xyz/verify?redirect=https://example.org",
        "https://microsoft-verify-account.example.top/login",
        "https://outlook.office365.mailbox-auth.example.click/reset",
        "https://appleid-confirm-billing.example.info/signin",
        "https://g.co/account/security",
        "https://gov-traffic-fine.example.click/pay",
    )

    for url in suspicious_urls:
        result = use_case.execute(CreateVerificationCommand(url=url))
        assert result.risk_assessment is not None
        assert result.risk_assessment.risk_level in {
            RiskLevel.LOW.value,
            RiskLevel.MEDIUM.value,
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        }


def test_manual_corpus_calibration_marks_redirected_login_style_destinations_as_caution() -> None:
    class RedirectResolver(RedirectResolverPort):
        def resolve(self, url: str) -> RedirectResolution:
            return RedirectResolution(
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

    use_case = _build_use_case(redirect_resolver=RedirectResolver())

    result = use_case.execute(CreateVerificationCommand(url="https://safe.example/link/123"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_level == RiskLevel.LOW.value
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in result.signals)
    assert any(
        signal.signal_type == "phishing_keywords"
        and signal.source == "resolved-destination-url-analyzer"
        for signal in result.signals
    )


def test_manual_corpus_calibration_benign_urls_remain_safe() -> None:
    use_case = _build_use_case()
    benign_urls = (
        "https://google.com/",
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

    google_auth_result = use_case.execute(
        CreateVerificationCommand(url="https://accounts.google.com/signin")
    )
    assert {signal.signal_type for signal in google_auth_result.signals} == {
        "recognized_reputable_domain"
    }

    microsoft_auth_result = use_case.execute(
        CreateVerificationCommand(url="https://login.microsoftonline.com/")
    )
    assert not microsoft_auth_result.signals


def test_manual_corpus_calibration_rejects_unsafe_local_targets() -> None:
    use_case = _build_use_case(public_target_validator=assert_safe_outbound_url)

    with pytest.raises(DomainException):
        use_case.execute(CreateVerificationCommand(url="https://localhost/login"))


def test_manual_corpus_calibration_rejects_single_label_targets() -> None:
    use_case = _build_use_case(public_target_validator=assert_safe_outbound_url)

    with pytest.raises(DomainException):
        use_case.execute(CreateVerificationCommand(url="A"))


def test_manual_corpus_calibration_marks_parked_pages_as_caution_or_worse() -> None:
    use_case = _build_use_case(
        html_fetcher=StaticHtmlFetcher(
            """
            <html>
              <body>
                <h1>This domain is for sale</h1>
                <p>Buy this domain with Sedo.</p>
              </body>
            </html>
            """
        )
    )

    result = use_case.execute(CreateVerificationCommand(url="https://for-sale-example.test/"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_level in {
        RiskLevel.LOW.value,
        RiskLevel.MEDIUM.value,
        RiskLevel.HIGH.value,
        RiskLevel.CRITICAL.value,
    }
    assert any(signal.signal_type == "low_information_page" for signal in result.signals)


def test_manual_corpus_calibration_marks_empty_root_pages_as_ambiguous_not_pristine() -> None:
    use_case = _build_use_case(
        html_fetcher=StaticHtmlFetcher(
            """
            <html>
              <body>
                <h1>Welcome</h1>
              </body>
            </html>
            """
        )
    )

    result = use_case.execute(CreateVerificationCommand(url="https://thin-example.test/"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.score < 100
    assert any(signal.signal_type == "low_information_page" for signal in result.signals)


def test_manual_corpus_calibration_treats_clean_shortener_redirects_as_safe() -> None:
    class ShortenerRedirectResolver(RedirectResolverPort):
        def resolve(self, url: str) -> RedirectResolution:
            return RedirectResolution(
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

    use_case = _build_use_case(redirect_resolver=ShortenerRedirectResolver())

    result = use_case.execute(CreateVerificationCommand(url="https://g.co/openai"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_level == RiskLevel.SAFE.value
    assert {signal.signal_type for signal in result.signals} == {
        "recognized_reputable_domain",
        "shortened_url",
    }


def test_manual_corpus_calibration_keeps_shortener_to_low_information_targets_in_caution() -> None:
    class ShortenerRedirectResolver(RedirectResolverPort):
        def resolve(self, url: str) -> RedirectResolution:
            return RedirectResolution(
                final_url="https://thin-example.test/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://bit.ly/abcd",
                        target_url="https://thin-example.test/",
                    ),
                ),
                provider_name="stub-redirect",
            )

    use_case = _build_use_case(
        redirect_resolver=ShortenerRedirectResolver(),
        html_fetcher=StaticHtmlFetcher(
            """
            <html>
              <body>
                <h1>Welcome</h1>
              </body>
            </html>
            """
        ),
    )

    result = use_case.execute(CreateVerificationCommand(url="https://bit.ly/abcd"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_level == RiskLevel.LOW.value
    assert any(signal.signal_type == "shortened_url" for signal in result.signals)
    assert any(signal.signal_type == "low_information_page" for signal in result.signals)
    assert all(signal.signal_type != "suspicious_redirect_chain" for signal in result.signals)


def test_manual_corpus_calibration_marks_shortener_to_questionable_tld_as_suspicious() -> None:
    class ShortenerRedirectResolver(RedirectResolverPort):
        def resolve(self, url: str) -> RedirectResolution:
            return RedirectResolution(
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

    use_case = _build_use_case(redirect_resolver=ShortenerRedirectResolver())

    result = use_case.execute(CreateVerificationCommand(url="https://bit.ly/abcd"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_level in {
        RiskLevel.LOW.value,
        RiskLevel.MEDIUM.value,
        RiskLevel.HIGH.value,
        RiskLevel.CRITICAL.value,
    }
    assert any(signal.signal_type == "shortened_url" for signal in result.signals)
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in result.signals)


def test_manual_corpus_calibration_strengthens_redirects_to_thin_questionable_destinations() -> None:
    class ShortenerRedirectResolver(RedirectResolverPort):
        def resolve(self, url: str) -> RedirectResolution:
            return RedirectResolution(
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

    use_case = _build_use_case(
        redirect_resolver=ShortenerRedirectResolver(),
        html_fetcher=StaticHtmlFetcher(
            """
            <html>
              <body>
                <h1>Welcome</h1>
              </body>
            </html>
            """
        ),
    )

    result = use_case.execute(CreateVerificationCommand(url="https://bit.ly/abcd"))

    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_level == RiskLevel.MEDIUM.value
    assert result.risk_assessment.score < 55
    assert any(signal.signal_type == "suspicious_redirect_chain" for signal in result.signals)
    assert any(signal.signal_type == "low_information_page" for signal in result.signals)


def test_manual_corpus_calibration_distinguishes_trusted_clean_from_unknown_clean() -> None:
    trusted_result = _build_use_case().execute(
        CreateVerificationCommand(url="https://openai.com/research")
    )

    unknown_result = _build_use_case().execute(
        CreateVerificationCommand(url="https://unknown-clean.example/")
    )

    assert trusted_result.risk_assessment is not None
    assert trusted_result.risk_assessment.risk_level == RiskLevel.SAFE.value
    assert trusted_result.risk_assessment.score > unknown_result.risk_assessment.score
    assert {
        signal.signal_type for signal in trusted_result.signals
    } == {"recognized_reputable_domain"}
    assert "Supporting trust context" in trusted_result.risk_assessment.summary
    assert "recognized_reputable_domain_bonus" not in trusted_result.risk_assessment.summary

    assert unknown_result.risk_assessment is not None
    assert unknown_result.risk_assessment.risk_level == RiskLevel.SAFE.value
    assert unknown_result.signals == ()
    assert "Compound pattern adjustments applied:" in unknown_result.risk_assessment.summary
    assert "evidence_light_clean_result" not in unknown_result.risk_assessment.summary
