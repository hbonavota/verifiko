from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.entities.analysis_trace_stage import AnalysisTraceStage
from app.domain.entities.score_breakdown import ScoreBreakdown
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.verdict_type import VerdictType
from app.domain.value_objects.confidence_score import ConfidenceScore


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    score: ConfidenceScore
    risk_level: RiskLevel
    verdict: VerdictType
    summary: str
    top_signals: tuple[str, ...]
    category_breakdown: dict[str, float]
    terminal_override: bool
    terminal_reason: str | None
    calculation_version: str
    analysis_warnings: tuple[str, ...] = ()
    analysis_trace: tuple[AnalysisTraceStage, ...] = ()
    score_breakdown: ScoreBreakdown | None = None
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
