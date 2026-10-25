from functools import cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.infrastructure.config.settings import get_settings

Base = declarative_base()
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def normalize_database_url(database_url: str) -> str:
    """Force the psycopg (v3) driver, which is the one we depend on.

    SQLAlchemy maps a bare ``postgresql://`` (and ``postgres://``) URL to the
    psycopg2 dialect by default, but this project only ships ``psycopg`` v3.
    Rewriting to ``postgresql+psycopg://`` keeps the app and the Alembic
    migration runner on the same driver regardless of how the URL is provided
    (e.g. a raw Neon connection string in a CI secret).
    """
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


# Backwards-compatible private alias (kept for existing imports/tests).
_normalize_database_url = normalize_database_url


def _resolved_database_url(database_url: str | None = None) -> str:
    if database_url is not None:
        return _normalize_database_url(database_url)
    return _normalize_database_url(get_settings().database_url)


def _engine_kwargs(database_url: str) -> dict:
    kwargs: dict = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


@cache
def get_engine(database_url: str | None = None) -> Engine:
    resolved_database_url = _resolved_database_url(database_url)
    return create_engine(resolved_database_url, **_engine_kwargs(resolved_database_url))


@cache
def get_session_factory(database_url: str | None = None) -> sessionmaker:
    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def drop_db(database_url: str | None = None) -> None:
    from app.infrastructure.persistence import models  # noqa: F401

    Base.metadata.drop_all(bind=get_engine(database_url))
