from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisSignalDTO:
    id: str
    signal_type: str
    category: str
    severity: str
    confidence: float
    detected: bool
    title: str
    description: str
    evidence: tuple[str, ...]
    source: str
    base_weight: float
    score_contribution: float
    tags: tuple[str, ...]
    created_at: str


@dataclass(frozen=True, slots=True)
class ExplanationFactorDTO:
    signal_type: str
    title: str
    source: str
    severity: str
    score_contribution: float
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisStageTraceDTO:
    stage: str
    source: str
    status: str
    signal_count: int
    signal_titles: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskExplanationDTO:
    headline: str
    decision_basis: str
    primary_factors: tuple[ExplanationFactorDTO, ...]
    analysis_trace: tuple[AnalysisStageTraceDTO, ...]
    coverage_warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisTraceDTO:
    layers_executed: tuple[str, ...]
    signals_by_source: dict[str, tuple[AnalysisSignalDTO, ...]]
    total_signals: int


@dataclass(frozen=True, slots=True)
class SignalContributionDTO:
    signal_type: str
    base_weight: float
    confidence: float
    impact: float


@dataclass(frozen=True, slots=True)
class CompoundRuleDeltaDTO:
    rule_name: str
    delta: float


@dataclass(frozen=True, slots=True)
class ScoreBreakdownDTO:
    base_score: float
    signal_contributions: tuple[SignalContributionDTO, ...]
    compound_rules_applied: tuple[CompoundRuleDeltaDTO, ...]
    final_score: float


@dataclass(frozen=True, slots=True)
class RiskAssessmentDTO:
    score: float
    risk_level: str
    verdict: str
    summary: str
    top_signals: tuple[str, ...]
    category_breakdown: dict[str, float]
    terminal_override: bool
    terminal_reason: str | None
    calculation_version: str
    analysis_warnings: tuple[str, ...]
    analysis_trace: tuple[AnalysisStageTraceDTO, ...]
    explanation: RiskExplanationDTO
    calculated_at: str


@dataclass(frozen=True, slots=True)
class VerificationDTO:
    id: str
    target_type: str
    original_input: str
    normalized_input: str
    status: str
    signals: tuple[AnalysisSignalDTO, ...]
    risk_assessment: RiskAssessmentDTO | None
    trace: AnalysisTraceDTO | None
    score_breakdown: ScoreBreakdownDTO | None
    created_at: str
    updated_at: str
    completed_at: str | None
    calculation_version: str
