from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.persistence.models.base_model import MagicLinkTokenModel
from app.infrastructure.persistence.repositories.sqlalchemy_magic_link_store import (
    SqlAlchemyMagicLinkStore,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now


def _store(clock: FakeClock) -> SqlAlchemyMagicLinkStore:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MagicLinkTokenModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return SqlAlchemyMagicLinkStore(factory, current_time_provider=clock)


def test_save_then_consume_returns_email_once() -> None:
    store = _store(FakeClock())
    store.save("hash-1", "user@example.com", 900)

    assert store.consume("hash-1") == "user@example.com"
    assert store.consume("hash-1") is None  # single use


def test_unknown_token_returns_none() -> None:
    store = _store(FakeClock())
    assert store.consume("missing") is None


def test_expired_token_returns_none() -> None:
    clock = FakeClock()
    store = _store(clock)
    store.save("hash-1", "user@example.com", 100)

    clock.now = clock.now.replace(minute=5)  # +5 min > 100s TTL
    assert store.consume("hash-1") is None
