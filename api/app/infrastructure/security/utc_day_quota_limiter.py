from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
import math
from threading import Lock
from typing import Callable

from app.infrastructure.security.utc_day_quota_status import UtcDayQuotaStatus


@dataclass(slots=True)
class UtcDayQuotaLimiter:
    daily_limit: int
    current_time_provider: Callable[[], datetime]
    _counts_by_day: dict[date, dict[str, int]] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def check(self, key: str) -> int | None:
        now = _as_utc(self.current_time_provider())
        current_day = now.date()
        with self._lock:
            status = self._get_status_unlocked(key, now=now, current_day=current_day)
            if status.remaining_today <= 0:
                return status.reset_in_seconds

            counts = self._counts_by_day.setdefault(current_day, {})
            counts[key] = status.used_today + 1
            return None

    def get_status(self, key: str) -> UtcDayQuotaStatus:
        now = _as_utc(self.current_time_provider())
        current_day = now.date()
        with self._lock:
            return self._get_status_unlocked(key, now=now, current_day=current_day)

    def reset(self) -> None:
        with self._lock:
            self._counts_by_day.clear()

    def _drop_stale_days(self, current_day: date) -> None:
        for tracked_day in tuple(self._counts_by_day):
            if tracked_day != current_day:
                self._counts_by_day.pop(tracked_day, None)

    def _get_status_unlocked(
        self,
        key: str,
        *,
        now: datetime,
        current_day: date,
    ) -> UtcDayQuotaStatus:
        next_midnight = datetime.combine(
            current_day + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        self._drop_stale_days(current_day)
        counts = self._counts_by_day.setdefault(current_day, {})
        used_today = counts.get(key, 0)
        remaining_today = max(0, self.daily_limit - used_today)
        reset_in_seconds = max(1, math.ceil((next_midnight - now).total_seconds()))
        return UtcDayQuotaStatus(
            daily_limit=self.daily_limit,
            used_today=used_today,
            remaining_today=remaining_today,
            reset_at_utc=next_midnight,
            reset_in_seconds=reset_in_seconds,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
