from dataclasses import dataclass
from datetime import UTC, datetime

from app.infrastructure.time.time_provider import TimeProvider


@dataclass(slots=True)
class SystemTimeProvider(TimeProvider):
    def now(self) -> datetime:
        return datetime.now(UTC)
