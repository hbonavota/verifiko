from dataclasses import dataclass

from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.user_id import UserId


@dataclass(frozen=True, slots=True)
class SignalInput:
    signal_type: SignalType
    category: SignalCategory
    severity: SignalSeverity
    confidence: float
    title: str
    description: str
    source: str
    evidence: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateVerificationCommand:
    url: str
    signals: tuple[SignalInput, ...] = ()
    calculation_version: str = "v1"
    user_id: UserId | None = None
