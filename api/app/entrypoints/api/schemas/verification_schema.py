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
    url: str
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
    calculated_at: str


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_type: str
    original_input: str
    normalized_input: str
    status: str
    signals: tuple[AnalysisSignalResponse, ...]
    risk_assessment: RiskAssessmentResponse | None
    created_at: str
    updated_at: str
    completed_at: str | None
    calculation_version: str
