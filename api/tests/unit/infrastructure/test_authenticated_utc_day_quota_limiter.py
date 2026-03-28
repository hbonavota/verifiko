from datetime import datetime, timezone

from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.authenticated_utc_day_quota_limiter import (
    AuthenticatedUtcDayQuotaLimiter,
)


def test_authenticated_utc_day_quota_limiter_tracks_each_user_separately() -> None:
    limiter = AuthenticatedUtcDayQuotaLimiter(
        quota_policy=UserQuotaPolicy(free_daily_limit=1, pro_daily_limit=2),
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )
    alice = User.create_google_user(
        email="alice@example.com",
        google_subject="google-sub-alice",
        display_name="Alice",
        avatar_url=None,
    )
    bob = User.create_google_user(
        email="bob@example.com",
        google_subject="google-sub-bob",
        display_name="Bob",
        avatar_url=None,
    )

    assert limiter.check(alice) is None
    assert limiter.check(bob) is None
    assert limiter.check(alice) == 43200


def test_authenticated_utc_day_quota_limiter_uses_higher_pro_limit() -> None:
    limiter = AuthenticatedUtcDayQuotaLimiter(
        quota_policy=UserQuotaPolicy(free_daily_limit=1, pro_daily_limit=2),
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
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
