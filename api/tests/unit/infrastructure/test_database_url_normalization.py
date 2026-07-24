"""Regression tests for database URL normalization.

The app depends on psycopg v3 only. SQLAlchemy resolves a bare ``postgresql://``
URL to the psycopg2 dialect, so both the app engine and the Alembic migration
runner must rewrite it to ``postgresql+psycopg://`` — otherwise a clean
environment (like the CI migration runner, which installs only what
``pyproject.toml`` declares) fails with ``ModuleNotFoundError: psycopg2``.
"""

import pytest

from app.infrastructure.persistence.database import normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require",
            "postgresql+psycopg://u:p@ep-x.neon.tech/neondb?sslmode=require",
        ),
        (
            "postgres://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
        (
            "postgresql+psycopg://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
        (
            "sqlite+pysqlite:///verifiko.sqlite3",
            "sqlite+pysqlite:///verifiko.sqlite3",
        ),
    ],
)
def test_normalize_database_url_forces_psycopg_v3_driver(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected


def test_normalized_postgres_url_resolves_to_psycopg_dialect() -> None:
    from sqlalchemy.engine.url import make_url

    url = make_url(normalize_database_url("postgresql://u:p@host/db"))
    assert url.drivername == "postgresql+psycopg"
