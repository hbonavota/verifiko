from app.infrastructure.security.redis_fixed_window_rate_limiter import (
    RedisFixedWindowRateLimiter,
)

from _fake_redis import FakeRedis


def test_redis_fixed_window_rate_limiter_blocks_after_limit_and_returns_retry_after() -> None:
    clock = {"now": 100.0}
    limiter = RedisFixedWindowRateLimiter(
        redis_client=FakeRedis(clock=lambda: clock["now"]),
        max_requests=2,
        window_seconds=10,
        now_provider=lambda: clock["now"],
    )

    assert limiter.check("203.0.113.10") is None
    clock["now"] = 101.0
    assert limiter.check("203.0.113.10") is None
    clock["now"] = 102.0
    assert limiter.check("203.0.113.10") == 8


def test_redis_fixed_window_rate_limiter_allows_after_window_expires() -> None:
    clock = {"now": 100.0}
    limiter = RedisFixedWindowRateLimiter(
        redis_client=FakeRedis(clock=lambda: clock["now"]),
        max_requests=1,
        window_seconds=10,
        now_provider=lambda: clock["now"],
    )

    assert limiter.check("203.0.113.10") is None
    clock["now"] = 111.0
    assert limiter.check("203.0.113.10") is None
