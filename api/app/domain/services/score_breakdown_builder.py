from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.score_breakdown import (
    CompoundRuleDelta,
    ScoreBreakdown,
    SignalContribution,
)
from app.domain.enums.signal_category import SignalCategory
from app.domain.services.compound_rules import CompoundRule, detected_types
from app.domain.services.scoring_policies import CATEGORY_CAPS, SEVERITY_MULTIPLIERS


def build_score_breakdown(
    signals: list[AnalysisSignal],
    compound_rules: list[CompoundRule],
    final_score: float,
) -> ScoreBreakdown:
    active_signals = [signal for signal in signals if signal.detected]
    raw_penalties = {id(signal): _signal_penalty(signal) for signal in active_signals}

    signals_by_category: dict[str, list[AnalysisSignal]] = {}
    for signal in active_signals:
        signals_by_category.setdefault(signal.category.value, []).append(signal)

    applied_impacts: dict[int, float] = {}
    for category_name, category_signals in signals_by_category.items():
        raw_total = sum(raw_penalties[id(signal)] for signal in category_signals)
        cap = CATEGORY_CAPS[SignalCategory(category_name)] if raw_total else 0.0
        ratio = min(1.0, cap / raw_total) if raw_total > 0 else 1.0
        for signal in category_signals:
            applied_impacts[id(signal)] = round(raw_penalties[id(signal)] * ratio, 2)

    signal_contributions = tuple(
        SignalContribution(
            signal_type=signal.signal_type.value,
            base_weight=signal.base_weight,
            confidence=signal.confidence.rounded(),
            impact=applied_impacts.get(id(signal), 0.0),
        )
        for signal in active_signals
    )

    types = detected_types(active_signals)
    compound_rules_applied = tuple(
        CompoundRuleDelta(rule_name=rule.name, delta=round(delta, 2))
        for rule in compound_rules
        for delta in [rule.evaluate(types)]
        if delta is not None
    )

    return ScoreBreakdown(
        base_score=100.0,
        signal_contributions=signal_contributions,
        compound_rules_applied=compound_rules_applied,
        final_score=round(final_score, 2),
    )


def _signal_penalty(signal: AnalysisSignal) -> float:
    multiplier = SEVERITY_MULTIPLIERS[signal.severity]
    return signal.base_weight * multiplier * signal.confidence.as_ratio
