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
    assert result.score_breakdown is not None
    assert result.score_breakdown.base_score == 100.0
    assert result.score_breakdown.final_score == 0
    assert result.score_breakdown.signal_contributions[0].signal_type == "blacklist_match"


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
    assert result.summary.startswith("Primary concern: brand or institution impersonation cues.")
    assert "Additional risk indicators were also detected." in result.summary
    assert "Compound pattern adjustments applied:" in result.summary
    assert "credential_lure_pattern" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "credential_lure_pattern"
        for entry in result.score_breakdown.compound_rules_applied
    )
    assert len(result.score_breakdown.signal_contributions) == 2


def test_infrastructure_compound_rule_adds_penalty() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN,
            category=SignalCategory.DOMAIN_REPUTATION,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(82),
            title="Suspicious infrastructure pattern",
            description="Reverse DNS points to dynamic residential hosting.",
            source="infrastructure-intelligence-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.PHISHING_KEYWORDS,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(85),
            title="Phishing keywords",
            description="Credential lure terms present",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.PHISHING_KEYWORDS],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value < 100
    assert "Compound pattern adjustments applied:" in result.summary
    assert "infrastructure_backed_credential_lure" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "infrastructure_backed_credential_lure"
        for entry in result.score_breakdown.compound_rules_applied
    )


def test_shortened_credential_lure_rule_adds_penalty() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.SHORTENED_URL,
            category=SignalCategory.NAVIGATION_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(82),
            title="Shortened destination",
            description="Known URL shortener.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SHORTENED_URL],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.PHISHING_KEYWORDS,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(69),
            title="Credential lure wording in URL",
            description="Credential lure terms present.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.PHISHING_KEYWORDS],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value < 100
    assert "Compound pattern adjustments applied:" in result.summary
    assert "shortened_credential_lure_pattern" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "shortened_credential_lure_pattern"
        for entry in result.score_breakdown.compound_rules_applied
    )


def test_shortened_redirected_lure_rule_adds_penalty() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.SHORTENED_URL,
            category=SignalCategory.NAVIGATION_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(82),
            title="Shortened destination",
            description="Known URL shortener.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SHORTENED_URL],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
            category=SignalCategory.NAVIGATION_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(88),
            title="Redirect chain crosses unrelated domains",
            description="Observed redirect chain changed domains.",
            source="redirect-resolver",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.BRAND_IMPERSONATION,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(92),
            title="Institution-style payment or penalty lure",
            description="Authority-style payment language on a non-official domain.",
            source="resolved-destination-url-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.BRAND_IMPERSONATION],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value < 100
    assert "Compound pattern adjustments applied:" in result.summary
    assert "shortened_redirected_lure_pattern" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "shortened_redirected_lure_pattern"
        for entry in result.score_breakdown.compound_rules_applied
    )


def test_redirected_credential_lure_rule_adds_penalty_without_shortener() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
            category=SignalCategory.NAVIGATION_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(85),
            title="Observed redirect chain",
            description="Observed redirect chain changed domains.",
            source="redirect-chain-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.PHISHING_KEYWORDS,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(69),
            title="Credential lure wording in URL",
            description="Credential lure terms present.",
            source="resolved-destination-url-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.PHISHING_KEYWORDS],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value == 78.42
    assert result.risk_level.value == "LOW"
    assert "redirected_credential_lure_pattern" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "redirected_credential_lure_pattern"
        for entry in result.score_breakdown.compound_rules_applied
    )


def test_low_information_landing_page_rule_adds_penalty() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.LOW_INFORMATION_PAGE,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(88),
            title="Parked or placeholder landing page",
            description="The page looks parked or non-informative.",
            source="html-credential-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.LOW_INFORMATION_PAGE],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value == 80
    assert "Compound pattern adjustments applied:" in result.summary
    assert "low_information_landing_page" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "low_information_landing_page"
        for entry in result.score_breakdown.compound_rules_applied
    )


def test_redirected_low_information_destination_rule_adds_penalty() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
            category=SignalCategory.NAVIGATION_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(85),
            title="Observed redirect chain",
            description="Observed redirect chain changed domains.",
            source="redirect-chain-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.LOW_INFORMATION_PAGE,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(72),
            title="Low-information landing page",
            description="The page contains almost no meaningful visible content.",
            source="resolved-destination-html-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.LOW_INFORMATION_PAGE],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value == 64.73
    assert result.risk_level.value == "LOW"
    assert "Compound pattern adjustments applied:" in result.summary
    assert "redirected_low_information_destination" not in result.summary
    assert result.score_breakdown is not None
    assert any(
        entry.rule_name == "redirected_low_information_destination"
        for entry in result.score_breakdown.compound_rules_applied
    )


def test_recognized_reputable_domain_bonus_improves_clean_score() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.RECOGNIZED_REPUTABLE_DOMAIN,
            category=SignalCategory.DOMAIN_REPUTATION,
            severity=SignalSeverity.LOW,
            confidence=ConfidenceScore(96),
            title="Recognized reputable domain",
            description="Conservative curated reputable domain match.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.RECOGNIZED_REPUTABLE_DOMAIN],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value == 100
    assert result.top_signals == ("Recognized reputable domain",)
    assert "Detected 0 risk signal(s)" in result.summary
    assert "Supporting trust context" in result.summary
    assert "Compound pattern adjustments applied:" in result.summary
    assert "recognized_reputable_domain_bonus" not in result.summary


def test_evidence_light_clean_result_penalizes_zero_signal_unknowns() -> None:
    engine = RiskScoringEngine()

    result = engine.calculate([], calculation_version="v1")

    assert result.score.value == 98
    assert result.summary.startswith("Detected 0 risk signal(s)")
    assert "Compound pattern adjustments applied:" in result.summary
    assert "evidence_light_clean_result" not in result.summary


def test_summary_falls_back_when_no_dominant_mapped_signal_exists() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.MISLEADING_SUBDOMAIN,
            category=SignalCategory.DOMAIN_STRUCTURE,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(88),
            title="Misleading subdomain structure",
            description="Unusual trust-signaling depth in the subdomain.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.MISLEADING_SUBDOMAIN],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.summary.startswith("Detected 1 risk signal(s)")
    assert "Primary concern:" not in result.summary


def test_safe_result_does_not_lead_with_primary_concern_even_with_dominant_signal() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
            category=SignalCategory.NAVIGATION_BEHAVIOR,
            severity=SignalSeverity.HIGH,
            confidence=ConfidenceScore(85),
            title="Observed redirect chain",
            description="Observed redirect chain changed domains.",
            source="redirect-chain-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.risk_level.value == "SAFE"
    assert result.summary.startswith("Detected 1 risk signal(s)")
    assert "Primary concern:" not in result.summary


def test_reputable_domain_bonus_does_not_override_suspicious_signals() -> None:
    engine = RiskScoringEngine()
    signals = [
        AnalysisSignal.create(
            signal_type=SignalType.RECOGNIZED_REPUTABLE_DOMAIN,
            category=SignalCategory.DOMAIN_REPUTATION,
            severity=SignalSeverity.LOW,
            confidence=ConfidenceScore(96),
            title="Recognized reputable domain",
            description="Conservative curated reputable domain match.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.RECOGNIZED_REPUTABLE_DOMAIN],
        ),
        AnalysisSignal.create(
            signal_type=SignalType.PHISHING_KEYWORDS,
            category=SignalCategory.CONTENT_BEHAVIOR,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(85),
            title="Credential lure wording in URL",
            description="Credential lure terms present.",
            source="url-rule-analyzer",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.PHISHING_KEYWORDS],
        ),
    ]

    result = engine.calculate(signals, calculation_version="v1")

    assert result.score.value < 100
    assert "recognized_reputable_domain_bonus" not in result.summary
