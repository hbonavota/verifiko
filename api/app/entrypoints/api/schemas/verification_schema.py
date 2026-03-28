from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType


class SignalInputPayload(BaseModel):
    signal_type: SignalType
    category: SignalCategory
    severity: SignalSeverity
    confidence: float = Field(ge=0, le=100)
    title: str
    description: str
    source: str
    evidence: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


class CreateVerificationRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)
    signals: tuple[SignalInputPayload, ...] = ()


class AnalysisSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class AnalysisTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    layers_executed: tuple[str, ...]
    signals_by_source: dict[str, tuple["AnalysisSignalResponse", ...]]
    total_signals: int


class SignalContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_type: str
    base_weight: float
    confidence: float
    impact: float


class CompoundRuleDeltaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_name: str
    delta: float


class ScoreBreakdownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    base_score: float
    signal_contributions: tuple[SignalContributionResponse, ...]
    compound_rules_applied: tuple[CompoundRuleDeltaResponse, ...]
    final_score: float


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    analysis_trace: tuple["AnalysisStageTraceResponse", ...]
    explanation: "RiskExplanationResponse"
    calculated_at: str


class ExplanationFactorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_type: str
    title: str
    source: str
    severity: str
    score_contribution: float
    evidence: tuple[str, ...]


class AnalysisStageTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: str
    source: str
    status: str
    signal_count: int
    signal_titles: tuple[str, ...]
    warnings: tuple[str, ...]


class RiskExplanationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    headline: str
    decision_basis: str
    primary_factors: tuple[ExplanationFactorResponse, ...]
    analysis_trace: tuple[AnalysisStageTraceResponse, ...]
    coverage_warnings: tuple[str, ...]


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_type: str
    original_input: str
    normalized_input: str
    status: str
    signals: tuple[AnalysisSignalResponse, ...]
    risk_assessment: RiskAssessmentResponse | None
    trace: AnalysisTraceResponse | None
    score_breakdown: ScoreBreakdownResponse | None
    created_at: str
    updated_at: str
    completed_at: str | None
    calculation_version: str
