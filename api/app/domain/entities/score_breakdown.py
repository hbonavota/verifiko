from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalContribution:
    signal_type: str
    base_weight: float
    confidence: float
    impact: float


@dataclass(frozen=True, slots=True)
class CompoundRuleDelta:
    rule_name: str
    delta: float


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    base_score: float
    signal_contributions: tuple[SignalContribution, ...]
    compound_rules_applied: tuple[CompoundRuleDelta, ...]
    final_score: float
