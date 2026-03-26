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
