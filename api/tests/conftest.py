from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.core.db import Base
from api.main import app


@pytest.fixture(scope="function")
def test_db():
    """Crea BD SQLite en memoria para tests"""
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Crear tablas
    Base.metadata.create_all(bind=engine)

    # Cargar schema SQL si existe
    schema_path = Path(__file__).parent / "schema_sqlite.sql"
    if schema_path.exists():
        schema_sql = schema_path.read_text(encoding="utf-8")
        if schema_sql.strip():
            with engine.begin() as conn:
                conn.connection.executescript(schema_sql)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(test_db):
    """Cliente FastAPI para tests"""
    from fastapi.testclient import TestClient

    from api.core.db import get_db

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)
