from dataclasses import dataclass
from datetime import datetime, timezone

from app.infrastructure.time.time_provider import TimeProvider


@dataclass(slots=True)
class SystemTimeProvider(TimeProvider):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
