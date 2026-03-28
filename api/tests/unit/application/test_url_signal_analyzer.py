from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.normalized_url import NormalizedUrl


def test_url_signal_analyzer_flags_punycode_homograph_hosts() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://xn--pple-43d.com/login"))

    assert any(signal.signal_type == SignalType.UNICODE_HOMOGRAPH for signal in signals)


def test_url_signal_analyzer_decodes_percent_encoded_lure_tokens() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://example.com/%256Cogin"))

    assert any(signal.signal_type == SignalType.PHISHING_KEYWORDS for signal in signals)


def test_url_signal_analyzer_uses_userinfo_in_brand_lure_detection() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://paypal.com@evil.example/login")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.BRAND_IMPERSONATION in signal_types
    assert SignalType.PHISHING_KEYWORDS in signal_types


def test_url_signal_analyzer_does_not_flag_official_brand_host_as_impersonation() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://onedrive.live.com/login"))

    assert all(signal.signal_type != SignalType.BRAND_IMPERSONATION for signal in signals)


def test_url_signal_analyzer_does_not_flag_official_auth_hosts_with_generic_login_terms() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    google_signals = analyzer.analyze(NormalizedUrl.from_raw("https://accounts.google.com/signin"))
    google_recovery_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://accounts.google.com/recovery")
    )
    microsoft_signals = analyzer.analyze(NormalizedUrl.from_raw("https://login.microsoftonline.com/"))

    assert {signal.signal_type for signal in google_signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }
    assert {signal.signal_type for signal in google_recovery_signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }
    assert microsoft_signals == []


def test_url_signal_analyzer_flags_recovery_and_verification_variants() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    recovery_signals = analyzer.analyze(NormalizedUrl.from_raw("https://collector.bad.example/recovery"))
    verification_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://collector.bad.example/verification")
    )

    assert any(signal.signal_type == SignalType.PHISHING_KEYWORDS for signal in recovery_signals)
    assert any(signal.signal_type == SignalType.PHISHING_KEYWORDS for signal in verification_signals)


def test_url_signal_analyzer_flags_government_brand_lure_domains() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://irs-verify.example.xyz/login"))

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.BRAND_IMPERSONATION in signal_types
    assert SignalType.PHISHING_KEYWORDS in signal_types


def test_url_signal_analyzer_flags_known_deceptive_brand_domain_fragments_in_subdomain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()
    cases = (
        (
            "http://paypal.com.security-check-login.com/",
            "paypal.com",
            "security-check-login.com",
            "paypal.com",
        ),
        (
            "https://appleid.apple.com.verify-session.security-check.net/",
            "appleid.apple.com",
            "security-check.net",
            "appleid.apple.com.verify-session",
        ),
        (
            "http://google.com.account-recovery-alert.user-verification.net/",
            "google.com",
            "user-verification.net",
            "google.com.account-recovery-alert",
        ),
    )

    for url, fragment, registered_domain, subdomain in cases:
        signals = analyzer.analyze(NormalizedUrl.from_raw(url))

        deceptive_signal = next(
            signal for signal in signals if signal.signal_type == SignalType.DECEPTIVE_BRAND_SUBDOMAIN
        )

        assert f"Observed deceptive fragment: {fragment}." in deceptive_signal.evidence
        assert f"Registered domain observed: {registered_domain}." in deceptive_signal.evidence
        assert f"Subdomain observed: {subdomain}." in deceptive_signal.evidence


def test_url_signal_analyzer_explains_long_deceptive_paypal_subdomain_chain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw(
            "http://paypal.com.security.check.login.system.update.confirm-account.info/"
        )
    )

    signal_types = {signal.signal_type for signal in signals}
    misleading_signal = next(
        signal for signal in signals if signal.signal_type == SignalType.MISLEADING_SUBDOMAIN
    )

    assert SignalType.DECEPTIVE_BRAND_SUBDOMAIN in signal_types
    assert SignalType.MISLEADING_SUBDOMAIN in signal_types
    assert (
        "Matched suspicious subdomain labels: login, security, system, update."
        in misleading_signal.evidence
    )
    assert "Subdomain label count observed: 7." in misleading_signal.evidence


def test_url_signal_analyzer_explains_long_deceptive_apple_subdomain_chain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw(
            "https://appleid.apple.com.verify.session.security-check-login.net/"
        )
    )

    signal_types = {signal.signal_type for signal in signals}
    misleading_signal = next(
        signal for signal in signals if signal.signal_type == SignalType.MISLEADING_SUBDOMAIN
    )

    assert SignalType.DECEPTIVE_BRAND_SUBDOMAIN in signal_types
    assert SignalType.MISLEADING_SUBDOMAIN in signal_types
    assert (
        "Matched suspicious subdomain labels: session, verify."
        in misleading_signal.evidence
    )
    assert "Subdomain label count observed: 5." in misleading_signal.evidence


def test_url_signal_analyzer_does_not_flag_official_brand_domains_as_deceptive_subdomain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    for url in (
        "https://paypal.com/",
        "https://appleid.apple.com/",
        "https://accounts.google.com/signin",
    ):
        signals = analyzer.analyze(NormalizedUrl.from_raw(url))

        assert all(
            signal.signal_type != SignalType.DECEPTIVE_BRAND_SUBDOMAIN for signal in signals
        )


def test_url_signal_analyzer_flags_deceptive_institution_domain_in_subdomain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://dgt.gob.es.multa-pendiente.secure-payments.xyz")
    )

    deceptive_signal = next(
        signal for signal in signals if signal.signal_type == SignalType.DECEPTIVE_BRAND_SUBDOMAIN
    )

    assert "Observed deceptive fragment: dgt.gob.es." in deceptive_signal.evidence
    assert "Registered domain observed: secure-payments.xyz." in deceptive_signal.evidence
    assert "Subdomain observed: dgt.gob.es.multa-pendiente." in deceptive_signal.evidence
    assert deceptive_signal.message_params["evidence"][0]["params"]["fragment"] == "dgt.gob.es"


def test_url_signal_analyzer_explains_long_deceptive_institution_subdomain_chain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://dgt.gob.es.multa.pendiente.secure.payments.confirmacion.xyz/")
    )

    signal_types = {signal.signal_type for signal in signals}
    misleading_signal = next(
        signal for signal in signals if signal.signal_type == SignalType.MISLEADING_SUBDOMAIN
    )

    assert SignalType.DECEPTIVE_BRAND_SUBDOMAIN in signal_types
    assert SignalType.MISLEADING_SUBDOMAIN in signal_types
    assert (
        "Matched suspicious subdomain labels: dgt, payments, secure."
        in misleading_signal.evidence
    )
    assert "Subdomain label count observed: 7." in misleading_signal.evidence


def test_url_signal_analyzer_strengthens_deep_deceptive_subdomain_chains() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://api.mail.google.com.security.example.net")
    )

    signal_types = {signal.signal_type for signal in signals}
    misleading_signal = next(
        signal for signal in signals if signal.signal_type == SignalType.MISLEADING_SUBDOMAIN
    )

    assert SignalType.DECEPTIVE_BRAND_SUBDOMAIN in signal_types
    assert SignalType.MISLEADING_SUBDOMAIN in signal_types
    assert "Registered domain observed: example.net." in misleading_signal.evidence
    assert "Subdomain observed: api.mail.google.com.security." in misleading_signal.evidence
    assert "Matched suspicious subdomain labels: security." in misleading_signal.evidence
    assert "Subdomain label count observed: 5." in misleading_signal.evidence


def test_url_signal_analyzer_does_not_flag_official_institution_domain_as_deceptive_subdomain() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://dgt.gob.es/multas"))

    assert all(signal.signal_type != SignalType.DECEPTIVE_BRAND_SUBDOMAIN for signal in signals)


def test_url_signal_analyzer_does_not_flag_official_deep_brand_subdomains_as_misleading() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://docs.paypal.com.developer.api.internal.paypal.com")
    )

    assert all(signal.signal_type != SignalType.DECEPTIVE_BRAND_SUBDOMAIN for signal in signals)
    assert all(signal.signal_type != SignalType.MISLEADING_SUBDOMAIN for signal in signals)


def test_url_signal_analyzer_flags_institution_mismatch_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://traffic-fine-payment.example.xyz/notice")
    )

    assert any(signal.signal_type == SignalType.BRAND_IMPERSONATION for signal in signals)
    assert any(signal.title == "Institution-style payment or penalty lure" for signal in signals)


def test_url_signal_analyzer_flags_risky_tld_for_institution_mismatch_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://gov-traffic-fine.example.click/pay")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.BRAND_IMPERSONATION in signal_types
    assert SignalType.TLD_TYPOSQUATTING in signal_types


def test_url_signal_analyzer_flags_branded_shorteners() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://g.co/account/security"))

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.SHORTENED_URL in signal_types
    assert SignalType.PHISHING_KEYWORDS in signal_types


def test_url_signal_analyzer_flags_mailbox_mfa_review_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://outlook.office365.mfa-review.mail-access.net/")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.PHISHING_KEYWORDS in signal_types
    assert SignalType.TACTICAL_EMAIL_STAGING in signal_types
    assert SignalType.BRAND_IMPERSONATION in signal_types


def test_url_signal_analyzer_flags_mailbox_otp_review_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://outlook.office365.otp-review.mail-access.net/")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.PHISHING_KEYWORDS in signal_types
    assert SignalType.TACTICAL_EMAIL_STAGING in signal_types
    assert SignalType.BRAND_IMPERSONATION in signal_types


def test_url_signal_analyzer_flags_mailbox_challenge_review_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://outlook.office365.challenge-review.mail-access.net/")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.PHISHING_KEYWORDS in signal_types
    assert SignalType.TACTICAL_EMAIL_STAGING in signal_types
    assert SignalType.BRAND_IMPERSONATION in signal_types


def test_url_signal_analyzer_flags_deceptive_reauth_brand_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://google.com.reauth-security-check.user-access.net/")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.PHISHING_KEYWORDS in signal_types
    assert SignalType.BRAND_IMPERSONATION in signal_types
    assert SignalType.DECEPTIVE_BRAND_SUBDOMAIN in signal_types


def test_url_signal_analyzer_flags_mailbox_session_review_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://outlook.office365.session-review.mail-access.net/")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.PHISHING_KEYWORDS in signal_types
    assert SignalType.TACTICAL_EMAIL_STAGING in signal_types
    assert SignalType.BRAND_IMPERSONATION in signal_types


def test_url_signal_analyzer_flags_deceptive_approve_brand_lures() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://google.com.approve-review.user-access.net/")
    )

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.PHISHING_KEYWORDS in signal_types
    assert SignalType.BRAND_IMPERSONATION in signal_types
    assert SignalType.DECEPTIVE_BRAND_SUBDOMAIN in signal_types


def test_url_signal_analyzer_does_not_flag_official_mfa_or_passkey_flows_as_phishing() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    google_signals = analyzer.analyze(NormalizedUrl.from_raw("https://accounts.google.com/passkey"))
    google_challenge_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://accounts.google.com/challenge")
    )
    google_approve_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://accounts.google.com/approve")
    )
    microsoft_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://login.microsoftonline.com/common/oauth2/authorize?mfa=required")
    )
    otp_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://login.microsoftonline.com/common/oauth2/authorize?otp=required")
    )
    reauth_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://login.microsoftonline.com/common/oauth2/authorize?reauth=true")
    )
    session_signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://dropbox.com/session")
    )

    assert {signal.signal_type for signal in google_signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }
    assert {signal.signal_type for signal in google_challenge_signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }
    assert {signal.signal_type for signal in google_approve_signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }
    assert microsoft_signals == []
    assert otp_signals == []
    assert reauth_signals == []
    assert session_signals == []


def test_url_signal_analyzer_flags_recognized_reputable_domains() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://docs.python.org/3/library"))

    assert {signal.signal_type for signal in signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }


def test_url_signal_analyzer_uses_structured_empty_and_none_placeholders() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://example.com/?next="))

    redirect_signal = next(
        signal for signal in signals if signal.signal_type == SignalType.SUSPICIOUS_REDIRECT_CHAIN
    )

    assert "Query parameter next=(empty) may steer navigation." in redirect_signal.evidence
    assert redirect_signal.message_params["evidence"][0]["params"]["value"] == {
        "key": "phrase.placeholder_empty_value",
        "params": {},
    }
