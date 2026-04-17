from datetime import datetime, timezone

from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.redis_utc_day_quota_limiter import (
    RedisAuthenticatedUtcDayQuotaLimiter,
    RedisUtcDayQuotaLimiter,
)


class FakeRedisPipeline:
    def __init__(self, client: "FakeRedisClient") -> None:
        self._client = client
        self._commands: list[tuple[str, str, int | None]] = []

    def __enter__(self) -> "FakeRedisPipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._commands.clear()

    def watch(self, key: str) -> None:
        return None

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def multi(self) -> None:
        return None

    def incr(self, key: str) -> None:
        self._commands.append(("incr", key, None))

    def expire(self, key: str, ttl: int) -> None:
        self._commands.append(("expire", key, ttl))

    def execute(self) -> list[int | bool]:
        results: list[int | bool] = []
        for command, key, value in self._commands:
            if command == "incr":
                results.append(self._client.incr(key))
            elif command == "expire":
                results.append(self._client.expire(key, value or 0))
        self._commands.clear()
        return results

    def unwatch(self) -> None:
        return None


class FakeRedisClient:
    def __init__(self) -> None:
        self._values: dict[str, int] = {}

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self)

    def get(self, key: str) -> str | None:
        value = self._values.get(key)
        return None if value is None else str(value)

    def incr(self, key: str) -> int:
        next_value = self._values.get(key, 0) + 1
        self._values[key] = next_value
        return next_value

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def scan_iter(self, match: str):
        prefix = match[:-1] if match.endswith("*") else match
        for key in tuple(self._values):
            if key.startswith(prefix):
                yield key

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._values:
                removed += 1
                self._values.pop(key, None)
        return removed


def test_redis_utc_day_quota_limiter_blocks_after_daily_limit_and_reports_status() -> None:
    limiter = RedisUtcDayQuotaLimiter(
        redis_client=FakeRedisClient(),
        daily_limit=2,
        current_time_provider=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
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
        redis_client=FakeRedisClient(),
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

    status = limiter.get_status(user)
    assert status.daily_limit == 2
    assert status.used_today == 2
    assert status.remaining_today == 0
