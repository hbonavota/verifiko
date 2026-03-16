from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.confidence_score import ConfidenceScore


@dataclass(frozen=True, slots=True)
class AnalysisSignal:
    id: UUID
    signal_type: SignalType
    category: SignalCategory
    severity: SignalSeverity
    confidence: ConfidenceScore
    detected: bool
    title: str
    description: str
    evidence: tuple[str, ...]
    source: str
    base_weight: float
    tags: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        signal_type: SignalType,
        category: SignalCategory,
        severity: SignalSeverity,
        confidence: ConfidenceScore,
        title: str,
        description: str,
        source: str,
        base_weight: float,
        evidence: tuple[str, ...] = (),
        detected: bool = True,
        tags: tuple[str, ...] = (),
    ) -> "AnalysisSignal":
        return AnalysisSignal(
            id=uuid4(),
            signal_type=signal_type,
            category=category,
            severity=severity,
            confidence=confidence,
            detected=detected,
            title=title,
            description=description,
            evidence=evidence,
            source=source,
            base_weight=base_weight,
            tags=tags,
        )
