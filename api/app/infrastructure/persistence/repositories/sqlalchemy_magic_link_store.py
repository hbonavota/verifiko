from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from app.application.ports.magic_link_store import MagicLinkStorePort
from app.infrastructure.persistence.models.base_model import MagicLinkTokenModel


class SqlAlchemyMagicLinkStore(MagicLinkStorePort):
    """Durable, shared single-use token store backed by the primary database.

    Postgres (or any shared DB) is used so a magic link stored in one request
    can be consumed in another — required on serverless where each invocation is
    a separate process. ``consume`` deletes and returns the row atomically, so a
    link is usable at most once.
    """

    def __init__(
        self,
        session_factory: sessionmaker,
        current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._session_factory = session_factory
        self._now = current_time_provider

    def save(self, token_hash: str, email: str, ttl_seconds: int) -> None:
        expires_at = self._now() + timedelta(seconds=ttl_seconds)
        with self._session_factory() as session:
            session.execute(
                delete(MagicLinkTokenModel).where(
                    MagicLinkTokenModel.token_hash == token_hash
                )
            )
            session.add(
                MagicLinkTokenModel(
                    token_hash=token_hash, email=email, expires_at=expires_at
                )
            )
            session.commit()

    def consume(self, token_hash: str) -> str | None:
        with self._session_factory() as session:
            result = session.execute(
                delete(MagicLinkTokenModel)
                .where(MagicLinkTokenModel.token_hash == token_hash)
                .returning(MagicLinkTokenModel.email, MagicLinkTokenModel.expires_at)
            )
            row = result.first()
            session.commit()

        if row is None:
            return None
        email, expires_at = row
        if _as_utc(expires_at) < self._now():
            return None
        return email


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
