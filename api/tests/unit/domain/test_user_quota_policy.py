from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.services.user_quota_policy import UserQuotaPolicy


def test_user_quota_policy_returns_free_limit_for_free_users() -> None:
    user = User.create_google_user(
        email="alice@example.com",
        google_subject="google-sub-alice",
        display_name="Alice",
        avatar_url=None,
    )

    policy = UserQuotaPolicy(free_daily_limit=20, pro_daily_limit=200)

    assert policy.daily_limit_for(user) == 20


def test_user_quota_policy_returns_pro_limit_for_pro_users() -> None:
    user = User.create_google_user(
        email="alice@example.com",
        google_subject="google-sub-alice",
        display_name="Alice",
        avatar_url=None,
    )
    user.assign_plan(UserPlan.PRO)

    policy = UserQuotaPolicy(free_daily_limit=20, pro_daily_limit=200)

    assert policy.daily_limit_for(user) == 200
