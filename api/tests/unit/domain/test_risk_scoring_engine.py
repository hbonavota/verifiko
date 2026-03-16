from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verdict_type import VerdictType
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.value_objects.confidence_score import ConfidenceScore


def test_terminal_override_for_high_confidence_blacklist_match() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.BLACKLIST_MATCH,
            category=SignalCategory.DOMAIN_REPUTATION,
            severity=SignalSeverity.CRITICAL,
            confidence=ConfidenceScore(99),
            title="Blacklist hit",
            description="Domain appears in critical feed",
            source="threat-feed",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.BLACKLIST_MATCH],
        )
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.terminal_override is True
    assert result.score.value == 0
    assert result.verdict is VerdictType.CONFIRMED_MALICIOUS


def test_compound_rule_adds_penalty() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.BRAND_IMPERSONATION,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(90),
            title="Brand impersonation",
            description="Visual impersonation detected",
            source="content-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.BRAND_IMPERSONATION],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.PHISHING_KEYWORDS,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(85),
            title="Phishing keywords",
            description="Credential lure terms present",
            source="nlp-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.PHISHING_KEYWORDS],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value < 100
    assert "credential_lure_pattern" in result.summary
