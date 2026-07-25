"""Pure, backend-agnostic helpers for UTC-day quota accounting.

Shared by every daily-quota limiter (Redis, SQLAlchemy, in-memory) so the status
maths and midnight/timezone handling live in exactly one place.
"""

from datetime import datetime, time, timedelta, timezone
import math

from app.infrastructure.security.utc_day_quota_status import UtcDayQuotaStatus


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def seconds_until_next_midnight(now: datetime) -> int:
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    return max(1, math.ceil((next_midnight - now).total_seconds()))


def status_for_used(*, used_today: int, daily_limit: int, now: datetime) -> UtcDayQuotaStatus:
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    return UtcDayQuotaStatus(
        daily_limit=daily_limit,
        used_today=used_today,
        remaining_today=max(0, daily_limit - used_today),
        reset_at_utc=next_midnight,
        reset_in_seconds=max(1, math.ceil((next_midnight - now).total_seconds())),
    )
