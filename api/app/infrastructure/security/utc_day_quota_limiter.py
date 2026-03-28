from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
import math
from threading import Lock
from typing import Callable


@dataclass(slots=True)
class UtcDayQuotaLimiter:
    daily_limit: int
    current_time_provider: Callable[[], datetime]
    _counts_by_day: dict[date, dict[str, int]] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def check(self, key: str) -> int | None:
        now = _as_utc(self.current_time_provider())
        current_day = now.date()
        next_midnight = datetime.combine(
            current_day + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        with self._lock:
            self._drop_stale_days(current_day)
            counts = self._counts_by_day.setdefault(current_day, {})
            current_count = counts.get(key, 0)

            if current_count >= self.daily_limit:
                retry_after = (next_midnight - now).total_seconds()
                return max(1, math.ceil(retry_after))

            counts[key] = current_count + 1
            return None

    def reset(self) -> None:
        with self._lock:
            self._counts_by_day.clear()

    def _drop_stale_days(self, current_day: date) -> None:
        for tracked_day in tuple(self._counts_by_day):
            if tracked_day != current_day:
                self._counts_by_day.pop(tracked_day, None)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
