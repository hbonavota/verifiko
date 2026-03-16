from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verdict_type import VerdictType
from app.domain.services.compound_rules import (
    BrandNewLookalikeDomainRule,
    CompoundRule,
    CredentialLurePatternRule,
    EmailFraudStagingPatternRule,
    RedirectedDeceptionPatternRule,
    detected_types,
)
from app.domain.services.scoring_policies import CATEGORY_CAPS, SEVERITY_MULTIPLIERS
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.confidence_score import ConfidenceScore


class RiskScoringEngine(ScoringService):
    def __init__(self, compound_rules: list[CompoundRule] | None = None) -> None:
        self._compound_rules = compound_rules or [
            BrandNewLookalikeDomainRule(),
            CredentialLurePatternRule(),
            EmailFraudStagingPatternRule(),
            RedirectedDeceptionPatternRule(),
        ]

    def calculate(self, signals: list[AnalysisSignal], calculation_version: str) -> RiskAssessment:
        active_signals = [signal for signal in signals if signal.detected]
        if _is_terminal_blacklist(active_signals):
            return RiskAssessment(
                score=ConfidenceScore(0),
                risk_level=RiskLevel.CRITICAL,
                verdict=VerdictType.CONFIRMED_MALICIOUS,
                summary="Terminal override triggered by high-confidence blacklist match.",
                top_signals=_top_signal_titles(active_signals),
                category_breakdown={},
                terminal_override=True,
                terminal_reason="blacklist_match confidence >= 0.98",
                calculation_version=calculation_version,
            )

        raw_category_penalties: dict[str, float] = {}
        signal_penalties: list[tuple[str, float]] = []

        for signal in active_signals:
            signal_penalty = _signal_penalty(signal)
            signal_penalties.append((signal.title, signal_penalty))
            key = signal.category.value
            raw_category_penalties[key] = raw_category_penalties.get(key, 0.0) + signal_penalty

        capped_category_penalties = {
            category.value: min(raw_category_penalties.get(category.value, 0.0), cap)
            for category, cap in CATEGORY_CAPS.items()
        }

        category_total_penalty = sum(capped_category_penalties.values())
        compound_penalty, triggered_rules = self._compound_penalty(active_signals)

        final_score_value = max(0.0, min(100.0, 100 - category_total_penalty - compound_penalty))
        final_score = ConfidenceScore(final_score_value)

        risk_level = _risk_level_for_score(final_score.value)
        verdict = _verdict_for_level(risk_level)

        summary = (
            f"Detected {len(active_signals)} signal(s); "
            f"category penalties={category_total_penalty:.2f}; "
            f"compound penalties={compound_penalty:.2f}."
        )
        if triggered_rules:
            summary = f"{summary} Rules: {', '.join(triggered_rules)}."

        return RiskAssessment(
            score=final_score,
            risk_level=risk_level,
            verdict=verdict,
            summary=summary,
            top_signals=_top_signal_titles_from_penalties(signal_penalties),
            category_breakdown=capped_category_penalties,
            terminal_override=False,
            terminal_reason=None,
            calculation_version=calculation_version,
        )

    def _compound_penalty(self, signals: list[AnalysisSignal]) -> tuple[float, list[str]]:
        types = detected_types(signals)
        total = 0.0
        triggered: list[str] = []
        for rule in self._compound_rules:
            penalty = rule.evaluate(types)
            if penalty is None:
                continue
            total += penalty
            triggered.append(rule.name)
        return total, triggered


def _signal_penalty(signal: AnalysisSignal) -> float:
    multiplier = SEVERITY_MULTIPLIERS[signal.severity]
    return signal.base_weight * multiplier * signal.confidence.as_ratio


def _risk_level_for_score(score: float) -> RiskLevel:
    if score >= 81:
        return RiskLevel.SAFE
    if score >= 61:
        return RiskLevel.LOW
    if score >= 41:
        return RiskLevel.MEDIUM
    if score >= 21:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _verdict_for_level(risk_level: RiskLevel) -> VerdictType:
    if risk_level is RiskLevel.SAFE:
        return VerdictType.TRUSTED
    if risk_level is RiskLevel.LOW:
        return VerdictType.CAUTION
    if risk_level is RiskLevel.MEDIUM:
        return VerdictType.SUSPICIOUS
    return VerdictType.LIKELY_MALICIOUS


def _is_terminal_blacklist(signals: list[AnalysisSignal]) -> bool:
    return any(
        signal.signal_type is SignalType.BLACKLIST_MATCH and signal.confidence.as_ratio >= 0.98
        for signal in signals
    )


def _top_signal_titles(signals: list[AnalysisSignal], max_items: int = 5) -> tuple[str, ...]:
    sorted_signals = sorted(signals, key=_signal_penalty, reverse=True)
    return tuple(signal.title for signal in sorted_signals[:max_items])


def _top_signal_titles_from_penalties(
    penalties: list[tuple[str, float]],
    max_items: int = 5,
) -> tuple[str, ...]:
    ranked = sorted(penalties, key=lambda item: item[1], reverse=True)
    return tuple(item[0] for item in ranked[:max_items])
