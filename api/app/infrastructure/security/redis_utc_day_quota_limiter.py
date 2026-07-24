from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import logging
import math
from typing import Any, Callable

from app.domain.entities.user import User
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.utc_day_quota_status import UtcDayQuotaStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RedisUtcDayQuotaLimiter:
    redis_client: Any
    daily_limit: int
    current_time_provider: Callable[[], datetime]
    key_prefix: str = "verifiko:quota:anonymous"

    def check(self, key: str) -> int | None:
        now = _as_utc(self.current_time_provider())
        try:
            used_today, allowed = _consume_if_available(
                redis_client=self.redis_client,
                redis_key=_redis_key(self.key_prefix, now.date(), key),
                daily_limit=self.daily_limit,
                reset_in_seconds=_seconds_until_next_midnight(now),
            )
        except Exception as exc:  # noqa: BLE001 - fail open on Redis outage/quota
            logger.warning("Daily quota limiter unavailable; failing open: %s", exc)
            return None
        if not allowed:
            return _status_for_used(
                used_today=used_today, daily_limit=self.daily_limit, now=now
            ).reset_in_seconds
        return None

    def get_status(self, key: str) -> UtcDayQuotaStatus:
        now = _as_utc(self.current_time_provider())
        used_today = _used_today_or_zero(
            self.redis_client, _redis_key(self.key_prefix, now.date(), key)
        )
        return _status_for_used(used_today=used_today, daily_limit=self.daily_limit, now=now)

    def reset(self) -> None:
        _reset_matching_keys(self.redis_client, f"{self.key_prefix}:*")


@dataclass(slots=True)
class RedisAuthenticatedUtcDayQuotaLimiter:
    redis_client: Any
    quota_policy: UserQuotaPolicy
    current_time_provider: Callable[[], datetime]
    key_prefix: str = "verifiko:quota:user"

    def check(self, user: User) -> int | None:
        now = _as_utc(self.current_time_provider())
        daily_limit = self.quota_policy.daily_limit_for(user)
        try:
            used_today, allowed = _consume_if_available(
                redis_client=self.redis_client,
                redis_key=_redis_key(self.key_prefix, now.date(), str(user.id)),
                daily_limit=daily_limit,
                reset_in_seconds=_seconds_until_next_midnight(now),
            )
        except Exception as exc:  # noqa: BLE001 - fail open on Redis outage/quota
            logger.warning("Authenticated quota limiter unavailable; failing open: %s", exc)
            return None
        if not allowed:
            return _status_for_used(
                used_today=used_today, daily_limit=daily_limit, now=now
            ).reset_in_seconds
        return None

    def get_status(self, user: User) -> UtcDayQuotaStatus:
        now = _as_utc(self.current_time_provider())
        daily_limit = self.quota_policy.daily_limit_for(user)
        used_today = _used_today_or_zero(
            self.redis_client, _redis_key(self.key_prefix, now.date(), str(user.id))
        )
        return _status_for_used(used_today=used_today, daily_limit=daily_limit, now=now)

    def reset(self) -> None:
        _reset_matching_keys(self.redis_client, f"{self.key_prefix}:*")


# Atomic check-then-increment evaluated server-side in a single Redis command.
# Returns {used, allowed} where allowed is 1 when the request was counted and 0
# when the caller was already at the daily limit (in which case the counter is
# NOT incremented, preserving the previous WATCH/MULTI semantics). One EVAL
# replaces the ~5-command optimistic-lock loop this used to run per request.
_QUOTA_CONSUME_SCRIPT = """
local limit = tonumber(ARGV[1])
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= limit then
  return {current, 0}
end
current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
end
return {current, 1}
"""


def _consume_if_available(
    *,
    redis_client: Any,
    redis_key: str,
    daily_limit: int,
    reset_in_seconds: int,
) -> tuple[int, bool]:
    result = redis_client.eval(
        _QUOTA_CONSUME_SCRIPT,
        1,
        redis_key,
        daily_limit,
        reset_in_seconds,
    )
    used = _coerce_count(result[0])
    allowed = bool(_coerce_count(result[1]))
    return used, allowed


def _used_today(redis_client: Any, redis_key: str) -> int:
    return _coerce_count(redis_client.get(redis_key))


def _used_today_or_zero(redis_client: Any, redis_key: str) -> int:
    try:
        return _used_today(redis_client, redis_key)
    except Exception as exc:  # noqa: BLE001 - report a permissive status on outage
        logger.warning("Quota status unavailable; reporting zero usage: %s", exc)
        return 0


def _status_for_used(*, used_today: int, daily_limit: int, now: datetime) -> UtcDayQuotaStatus:
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


def _redis_key(prefix: str, current_day: date, identifier: str) -> str:
    return f"{prefix}:{current_day.isoformat()}:{identifier}"


def _seconds_until_next_midnight(now: datetime) -> int:
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    return max(1, math.ceil((next_midnight - now).total_seconds()))


def _coerce_count(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _reset_matching_keys(redis_client: Any, pattern: str) -> None:
    keys = list(redis_client.scan_iter(match=pattern))
    if keys:
        redis_client.delete(*keys)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
