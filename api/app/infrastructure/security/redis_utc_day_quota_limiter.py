import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.domain.entities.user import User
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.utc_day_quota_math import (
    as_utc as _as_utc,
)
from app.infrastructure.security.utc_day_quota_math import (
    seconds_until_next_midnight as _seconds_until_next_midnight,
)
from app.infrastructure.security.utc_day_quota_math import (
    status_for_used as _status_for_used,
)
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
        return _status_for_used(
            used_today=used_today, daily_limit=self.daily_limit, now=now
        )

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
            logger.warning(
                "Authenticated quota limiter unavailable; failing open: %s", exc
            )
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


def _redis_key(prefix: str, current_day: date, identifier: str) -> str:
    return f"{prefix}:{current_day.isoformat()}:{identifier}"


def _coerce_count(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _reset_matching_keys(redis_client: Any, pattern: str) -> None:
    keys = list(redis_client.scan_iter(match=pattern))
    if keys:
        redis_client.delete(*keys)
