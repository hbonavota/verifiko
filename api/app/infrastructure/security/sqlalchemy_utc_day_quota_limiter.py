from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.domain.entities.user import User
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.infrastructure.security.utc_day_quota_math import (
    as_utc,
    seconds_until_next_midnight,
    status_for_used,
)
from app.infrastructure.security.utc_day_quota_status import UtcDayQuotaStatus

logger = logging.getLogger(__name__)

# Atomic check-then-increment in a single statement. A fresh day inserts used=1;
# an existing counter is bumped only while it is still under the limit. When the
# caller is already at the limit the conditional DO UPDATE matches no row and
# RETURNING yields nothing, so the counter is never over-incremented. The syntax
# is shared by Postgres and modern SQLite (>= 3.35 for RETURNING).
_CONSUME_SQL = text("""
    INSERT INTO daily_quota_counters (identity_key, quota_day, used)
    VALUES (:identity_key, :quota_day, 1)
    ON CONFLICT (identity_key, quota_day)
    DO UPDATE SET used = daily_quota_counters.used + 1
    WHERE daily_quota_counters.used < :daily_limit
    RETURNING used
    """)

_STATUS_SQL = text("""
    SELECT used FROM daily_quota_counters
    WHERE identity_key = :identity_key AND quota_day = :quota_day
    """)


def _consume(
    session_factory: sessionmaker,
    *,
    identity_key: str,
    now: datetime,
    daily_limit: int,
) -> int | None:
    """Atomically count one request. Returns the new ``used`` when allowed, or
    ``None`` when the caller is already at the daily limit."""
    if daily_limit <= 0:
        return None
    with session_factory() as session:
        row = session.execute(
            _CONSUME_SQL,
            {
                "identity_key": identity_key,
                "quota_day": now.date().isoformat(),
                "daily_limit": daily_limit,
            },
        ).first()
        session.commit()
    return int(row[0]) if row is not None else None


def _used_today(
    session_factory: sessionmaker, *, identity_key: str, now: datetime
) -> int:
    with session_factory() as session:
        row = session.execute(
            _STATUS_SQL,
            {"identity_key": identity_key, "quota_day": now.date().isoformat()},
        ).first()
    return int(row[0]) if row is not None else 0


def _reset_namespace(session_factory: sessionmaker, namespace: str) -> None:
    with session_factory() as session:
        session.execute(
            text("DELETE FROM daily_quota_counters WHERE identity_key LIKE :pattern"),
            {"pattern": f"{namespace}:%"},
        )
        session.commit()


@dataclass(slots=True)
class SqlAlchemyUtcDayQuotaLimiter:
    """Durable anonymous daily quota backed by Postgres (S3-compatible SQLite in
    tests). Mirrors ``RedisUtcDayQuotaLimiter`` but keeps the counter in the
    primary database, so it survives restarts and never depends on Redis."""

    session_factory: sessionmaker
    daily_limit: int
    current_time_provider: Callable[[], datetime]
    key_namespace: str = "anonymous"

    def check(self, key: str) -> int | None:
        now = as_utc(self.current_time_provider())
        try:
            used = _consume(
                self.session_factory,
                identity_key=self._identity_key(key),
                now=now,
                daily_limit=self.daily_limit,
            )
        except Exception as exc:  # noqa: BLE001 - fail open on DB outage
            logger.warning("Daily quota limiter unavailable; failing open: %s", exc)
            return None
        if used is None:
            return seconds_until_next_midnight(now)
        return None

    def get_status(self, key: str) -> UtcDayQuotaStatus:
        now = as_utc(self.current_time_provider())
        used_today = self._used_today_or_zero(self._identity_key(key), now)
        return status_for_used(
            used_today=used_today, daily_limit=self.daily_limit, now=now
        )

    def reset(self) -> None:
        _reset_namespace(self.session_factory, self.key_namespace)

    def _identity_key(self, key: str) -> str:
        return f"{self.key_namespace}:{key}"

    def _used_today_or_zero(self, identity_key: str, now: datetime) -> int:
        try:
            return _used_today(self.session_factory, identity_key=identity_key, now=now)
        except Exception as exc:  # noqa: BLE001 - permissive status on outage
            logger.warning("Quota status unavailable; reporting zero usage: %s", exc)
            return 0


@dataclass(slots=True)
class SqlAlchemyAuthenticatedUtcDayQuotaLimiter:
    """Durable per-user daily quota backed by Postgres. The daily limit comes
    from the caller's plan via ``UserQuotaPolicy``."""

    session_factory: sessionmaker
    quota_policy: UserQuotaPolicy
    current_time_provider: Callable[[], datetime]
    key_namespace: str = "user"

    def check(self, user: User) -> int | None:
        now = as_utc(self.current_time_provider())
        daily_limit = self.quota_policy.daily_limit_for(user)
        try:
            used = _consume(
                self.session_factory,
                identity_key=self._identity_key(user),
                now=now,
                daily_limit=daily_limit,
            )
        except Exception as exc:  # noqa: BLE001 - fail open on DB outage
            logger.warning(
                "Authenticated quota limiter unavailable; failing open: %s", exc
            )
            return None
        if used is None:
            return seconds_until_next_midnight(now)
        return None

    def get_status(self, user: User) -> UtcDayQuotaStatus:
        now = as_utc(self.current_time_provider())
        daily_limit = self.quota_policy.daily_limit_for(user)
        used_today = self._used_today_or_zero(self._identity_key(user), now)
        return status_for_used(used_today=used_today, daily_limit=daily_limit, now=now)

    def reset(self) -> None:
        _reset_namespace(self.session_factory, self.key_namespace)

    def _identity_key(self, user: User) -> str:
        return f"{self.key_namespace}:{user.id}"

    def _used_today_or_zero(self, identity_key: str, now: datetime) -> int:
        try:
            return _used_today(self.session_factory, identity_key=identity_key, now=now)
        except Exception as exc:  # noqa: BLE001 - permissive status on outage
            logger.warning("Quota status unavailable; reporting zero usage: %s", exc)
            return 0
