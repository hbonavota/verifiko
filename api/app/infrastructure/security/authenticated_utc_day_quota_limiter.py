from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
import math
from threading import Lock
from typing import Callable

from app.domain.entities.user import User
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.utc_day_quota_status import UtcDayQuotaStatus


@dataclass(slots=True)
class AuthenticatedUtcDayQuotaLimiter:
    quota_policy: UserQuotaPolicy
    current_time_provider: Callable[[], datetime]
    _counts_by_day: dict[date, dict[str, int]] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def check(self, user: User) -> int | None:
        now = _as_utc(self.current_time_provider())
        current_day = now.date()
        with self._lock:
            status = self._get_status_unlocked(user, now=now, current_day=current_day)
            if status.remaining_today <= 0:
                return status.reset_in_seconds

            counts = self._counts_by_day.setdefault(current_day, {})
            counts[str(user.id)] = status.used_today + 1
            return None

    def get_status(self, user: User) -> UtcDayQuotaStatus:
        now = _as_utc(self.current_time_provider())
        current_day = now.date()
        with self._lock:
            return self._get_status_unlocked(user, now=now, current_day=current_day)

    def reset(self) -> None:
        with self._lock:
            self._counts_by_day.clear()

    def _drop_stale_days(self, current_day: date) -> None:
        for tracked_day in tuple(self._counts_by_day):
            if tracked_day != current_day:
                self._counts_by_day.pop(tracked_day, None)

    def _get_status_unlocked(
        self,
        user: User,
        *,
        now: datetime,
        current_day: date,
    ) -> UtcDayQuotaStatus:
        next_midnight = datetime.combine(
            current_day + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        user_key = str(user.id)
        daily_limit = self.quota_policy.daily_limit_for(user)
        self._drop_stale_days(current_day)
        counts = self._counts_by_day.setdefault(current_day, {})
        used_today = counts.get(user_key, 0)
        remaining_today = max(0, daily_limit - used_today)
        reset_in_seconds = max(1, math.ceil((next_midnight - now).total_seconds()))
        return UtcDayQuotaStatus(
            daily_limit=daily_limit,
            used_today=used_today,
            remaining_today=remaining_today,
            reset_at_utc=next_midnight,
            reset_in_seconds=reset_in_seconds,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
