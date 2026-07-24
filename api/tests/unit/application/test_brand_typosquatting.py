import pytest

from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.signal_type import SignalType
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.normalized_url import NormalizedUrl


def _typosquat_signals(url: str):
    analyzer = DeterministicUrlSignalAnalyzer()
    signals = analyzer.analyze(NormalizedUrl.from_raw(url))
    return [s for s in signals if s.signal_type == SignalType.BRAND_TYPOSQUATTING]


@pytest.mark.parametrize(
    "url",
    [
        "https://paypa1.com/login",       # l -> 1 leetspeak
        "https://g00gle.com/",            # o -> 0 (twice)
        "https://micr0soft.com/account",  # o -> 0
        "https://amazn.com/",             # single deletion
        "https://netfllix.com/",          # single insertion
        "https://faceb00k.com/login",     # o -> 0 (twice)
    ],
)
def test_flags_brand_look_alike_domains(url: str) -> None:
    matches = _typosquat_signals(url)
    assert len(matches) == 1
    assert matches[0].signal_type == SignalType.BRAND_TYPOSQUATTING


@pytest.mark.parametrize(
    "url",
    [
        "https://paypal.com/login",       # the real brand, exact
        "https://www.google.com/",        # official brand host
        "https://example.com/login",      # unrelated
        "https://github.com/",            # unrelated legitimate
        "https://apple.com/",             # exact brand token, not a typo
    ],
)
def test_does_not_flag_legitimate_or_unrelated_domains(url: str) -> None:
    assert _typosquat_signals(url) == []


def test_typosquat_signal_carries_brand_evidence() -> None:
    matches = _typosquat_signals("https://paypa1.com/verify")
    assert matches, "expected a typosquat signal"
    signal = matches[0]
    # The impersonated brand should be surfaced in the localized evidence.
    rendered = " ".join(signal.evidence).lower() if signal.evidence else ""
    assert "paypal" in rendered or "paypa1" in rendered


def test_lone_typosquat_escalates_to_at_least_suspicious() -> None:
    # A confirmed brand look-alike is decisive on its own: it must not score as a
    # merely-LOW / SAFE result even without any other signal.
    analyzer = DeterministicUrlSignalAnalyzer()
    signals = analyzer.analyze(NormalizedUrl.from_raw("https://g00gle.com/"))
    assessment = RiskScoringEngine().calculate(signals, calculation_version="test")
    assert assessment.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
