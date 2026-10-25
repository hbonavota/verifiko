from datetime import UTC, datetime

from _fake_redis import FakeRedis

from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.redis_utc_day_quota_limiter import (
    RedisAuthenticatedUtcDayQuotaLimiter,
    RedisUtcDayQuotaLimiter,
)


def test_redis_utc_day_quota_limiter_blocks_after_daily_limit_and_reports_status() -> (
    None
):
    limiter = RedisUtcDayQuotaLimiter(
        redis_client=FakeRedis(),
        daily_limit=2,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
    )

    assert limiter.check("203.0.113.10") is None
    assert limiter.check("203.0.113.10") is None
    assert limiter.check("203.0.113.10") == 43200

    status = limiter.get_status("203.0.113.10")
    assert status.daily_limit == 2
    assert status.used_today == 2
    assert status.remaining_today == 0


def test_redis_authenticated_utc_day_quota_limiter_uses_plan_limits() -> None:
    limiter = RedisAuthenticatedUtcDayQuotaLimiter(
        redis_client=FakeRedis(),
        quota_policy=UserQuotaPolicy(free_daily_limit=1, pro_daily_limit=2),
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
    )
    user = User.create_google_user(
        email="alice@example.com",
        google_subject="google-sub-alice",
        display_name="Alice",
        avatar_url=None,
    )
    user.assign_plan(UserPlan.PRO)

    assert limiter.check(user) is None
    assert limiter.check(user) is None
    assert limiter.check(user) == 43200

    status = limiter.get_status(user)
    assert status.daily_limit == 2
    assert status.used_today == 2
    assert status.remaining_today == 0
