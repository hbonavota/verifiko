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
    microsoft_signals = analyzer.analyze(NormalizedUrl.from_raw("https://login.microsoftonline.com/"))

    assert {signal.signal_type for signal in google_signals} == {
        SignalType.RECOGNIZED_REPUTABLE_DOMAIN
    }
    assert microsoft_signals == []


def test_url_signal_analyzer_flags_government_brand_lure_domains() -> None:
    analyzer = DeterministicUrlSignalAnalyzer()

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://irs-verify.example.xyz/login"))

    signal_types = {signal.signal_type for signal in signals}
    assert SignalType.BRAND_IMPERSONATION in signal_types
    assert SignalType.PHISHING_KEYWORDS in signal_types


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
