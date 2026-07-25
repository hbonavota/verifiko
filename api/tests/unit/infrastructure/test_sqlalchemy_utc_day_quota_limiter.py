from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.persistence.database import Base
import app.infrastructure.persistence.models  # noqa: F401 - register ORM models
from app.infrastructure.security.sqlalchemy_utc_day_quota_limiter import (
    SqlAlchemyAuthenticatedUtcDayQuotaLimiter,
    SqlAlchemyUtcDayQuotaLimiter,
)


def _memory_session_factory() -> sessionmaker:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


class _Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def _user(plan: UserPlan = UserPlan.FREE) -> User:
    user = User.create_google_user(
        email="alice@example.com",
        google_subject="google-sub-alice",
        display_name="Alice",
        avatar_url=None,
    )
    if plan is not UserPlan.FREE:
        user.assign_plan(plan)
    return user


def test_counts_each_request_and_status_reflects_usage() -> None:
    limiter = SqlAlchemyUtcDayQuotaLimiter(
        session_factory=_memory_session_factory(),
        daily_limit=3,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )

    assert limiter.check("client-1") is None
    assert limiter.check("client-1") is None

    status = limiter.get_status("client-1")
    assert status.used_today == 2
    assert status.remaining_today == 1
    assert status.daily_limit == 3


def test_blocks_at_the_limit_with_retry_after() -> None:
    limiter = SqlAlchemyUtcDayQuotaLimiter(
        session_factory=_memory_session_factory(),
        daily_limit=2,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )

    assert limiter.check("client-1") is None
    assert limiter.check("client-1") is None
    # Third request in the same UTC day is blocked; retry-after = seconds to midnight.
    assert limiter.check("client-1") == 43200
    # The blocked attempt did not over-count the counter.
    assert limiter.get_status("client-1").used_today == 2


def test_separate_identities_do_not_share_a_counter() -> None:
    limiter = SqlAlchemyUtcDayQuotaLimiter(
        session_factory=_memory_session_factory(),
        daily_limit=1,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )

    assert limiter.check("client-1") is None
    assert limiter.check("client-2") is None
    assert limiter.check("client-1") == 43200


def test_counter_rolls_over_to_a_fresh_day() -> None:
    clock = _Clock(datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc))
    limiter = SqlAlchemyUtcDayQuotaLimiter(
        session_factory=_memory_session_factory(),
        daily_limit=1,
        current_time_provider=clock.now,
    )

    assert limiter.check("client-1") is None
    assert limiter.check("client-1") == 43200

    clock.value = datetime(2026, 3, 29, 9, 0, tzinfo=timezone.utc)
    # A new quota_day means a fresh counter.
    assert limiter.check("client-1") is None
    assert limiter.get_status("client-1").used_today == 1


def test_authenticated_limiter_uses_plan_limit() -> None:
    factory = _memory_session_factory()
    limiter = SqlAlchemyAuthenticatedUtcDayQuotaLimiter(
        session_factory=factory,
        quota_policy=UserQuotaPolicy(free_daily_limit=1, pro_daily_limit=3),
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )

    free_user = _user(UserPlan.FREE)
    assert limiter.check(free_user) is None
    assert limiter.check(free_user) == 43200

    pro_user = _user(UserPlan.PRO)
    assert limiter.check(pro_user) is None
    assert limiter.check(pro_user) is None
    assert limiter.check(pro_user) is None
    assert limiter.check(pro_user) == 43200


def _boom_factory():
    def _factory():
        raise RuntimeError("database is down")

    return _factory


def test_check_fails_open_on_database_error() -> None:
    limiter = SqlAlchemyUtcDayQuotaLimiter(
        session_factory=_boom_factory(),
        daily_limit=1,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )

    # A DB outage must not raise or block; the request is allowed.
    assert limiter.check("client-1") is None


def test_status_reports_permissive_on_database_error() -> None:
    limiter = SqlAlchemyUtcDayQuotaLimiter(
        session_factory=_boom_factory(),
        daily_limit=10,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
    )

    status = limiter.get_status("client-1")
    assert status.used_today == 0
    assert status.remaining_today == 10
