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
    tags: tuple[str, ...]
    created_at: str


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
    created_at: str
    updated_at: str
    completed_at: str | None
    calculation_version: str
