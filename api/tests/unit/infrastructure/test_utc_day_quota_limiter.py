from datetime import datetime, timezone

from app.infrastructure.security.utc_day_quota_limiter import UtcDayQuotaLimiter


def test_utc_day_quota_limiter_blocks_after_daily_limit_and_returns_retry_after_to_midnight() -> None:
    current_time = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    limiter = UtcDayQuotaLimiter(
        daily_limit=2,
        current_time_provider=lambda: current_time,
    )

    assert limiter.check("203.0.113.10") is None
    assert limiter.check("203.0.113.10") is None
    assert limiter.check("203.0.113.10") == 43200


def test_utc_day_quota_limiter_resets_counts_after_utc_midnight() -> None:
    current_time = datetime(2026, 3, 28, 23, 59, 58, tzinfo=timezone.utc)
    limiter = UtcDayQuotaLimiter(
        daily_limit=1,
        current_time_provider=lambda: current_time,
    )

    assert limiter.check("203.0.113.10") is None
    assert limiter.check("203.0.113.10") == 2

    current_time = datetime(2026, 3, 29, 0, 0, 1, tzinfo=timezone.utc)
    assert limiter.check("203.0.113.10") is None
