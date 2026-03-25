from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.entrypoints.api.dependencies.container import get_verification_repository
from app.entrypoints.api.main import app
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import drop_db, get_engine, get_session_factory
from tests.integration.alembic_helpers import upgrade_to_head


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "verifiko-api.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"

    monkeypatch.setenv("DATABASE_URL", database_url)

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_verification_repository.cache_clear()

    upgrade_to_head(database_url)

    with TestClient(app) as test_client:
        yield test_client

    drop_db()
    get_verification_repository.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_verification_api_create_list_and_get(client: TestClient) -> None:
    create_response = client.post(
        "/api/verifications",
        json={
            "url": "verifiko.es/login",
            "signals": [
                {
                    "signal_type": "brand_impersonation",
                    "category": "content_behavior",
                    "severity": "HIGH",
                    "confidence": 92,
                    "title": "Brand impersonation",
                    "description": "Brand styling copied from the legitimate destination.",
                    "source": "content-analyzer",
                    "evidence": ["Logo and typography match the target brand."],
                    "tags": ["brand", "visual-match"],
                }
            ],
        },
    )

    assert create_response.status_code == 201
    created_body = create_response.json()
    assert created_body["status"] == "COMPLETED"
    assert created_body["risk_assessment"]["risk_level"] in {
        "SAFE",
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    verification_id = created_body["id"]

    list_response = client.get("/api/verifications")
    assert list_response.status_code == 200
    listed_items = list_response.json()
    assert len(listed_items) == 1
    assert listed_items[0]["id"] == verification_id

    get_response = client.get(f"/api/verifications/{verification_id}")
    assert get_response.status_code == 200
    fetched_body = get_response.json()
    assert fetched_body["id"] == verification_id
    assert fetched_body["normalized_input"] == "https://verifiko.es/login"


def test_verification_api_can_generate_signals_from_url_only(client: TestClient) -> None:
    create_response = client.post(
        "/api/verifications",
        json={
            "url": "http://paypal-login-security-check.example.xyz/verify?redirect=https://example.org",
        },
    )

    assert create_response.status_code == 201
    created_body = create_response.json()
    assert created_body["signals"]
    assert created_body["risk_assessment"] is not None


def test_verification_api_returns_404_for_missing_verification(client: TestClient) -> None:
    response = client.get("/api/verifications/550e8400-e29b-41d4-a716-446655440099")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Verification not found: 550e8400-e29b-41d4-a716-446655440099"
    )
