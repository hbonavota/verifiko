from datetime import datetime, timezone

from app.infrastructure.security.redis_fixed_window_rate_limiter import (
    RedisFixedWindowRateLimiter,
)
from app.infrastructure.security.redis_utc_day_quota_limiter import (
    RedisUtcDayQuotaLimiter,
)


class ExplodingRedis:
    """Simulates Redis being unavailable / over its command quota."""

    def pipeline(self):
        raise RuntimeError("max requests limit exceeded")

    def get(self, key):
        raise RuntimeError("max requests limit exceeded")


def test_fixed_window_limiter_fails_open_on_redis_error() -> None:
    limiter = RedisFixedWindowRateLimiter(
        redis_client=ExplodingRedis(), max_requests=1, window_seconds=60
    )
    # A Redis outage must not raise; the request is allowed (None = no retry-after).
    assert limiter.check("client-1") is None


def test_daily_quota_limiter_fails_open_on_redis_error() -> None:
    limiter = RedisUtcDayQuotaLimiter(
        redis_client=ExplodingRedis(),
        daily_limit=3,
        current_time_provider=lambda: datetime(2026, 7, 23, 12, tzinfo=timezone.utc),
    )
    assert limiter.check("client-1") is None


def test_daily_quota_status_reports_permissive_on_redis_error() -> None:
    limiter = RedisUtcDayQuotaLimiter(
        redis_client=ExplodingRedis(),
        daily_limit=10,
        current_time_provider=lambda: datetime(2026, 7, 23, 12, tzinfo=timezone.utc),
    )
    status = limiter.get_status("client-1")
    assert status.used_today == 0
    assert status.remaining_today == 10
