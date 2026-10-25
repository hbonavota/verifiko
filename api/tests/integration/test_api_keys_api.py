from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.entrypoints.api.dependencies.container as container
from app.entrypoints.api.dependencies.container import (
    get_api_key_repository,
    get_api_key_token_service,
    get_user_repository,
    get_verification_repository,
)
from app.entrypoints.api.main import app
from app.infrastructure.persistence.database import (
    drop_db,
    get_engine,
    get_session_factory,
)
from tests.integration.alembic_helpers import upgrade_to_head


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "verifiko-api-keys.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "test-auth-secret")

    _clear_caches()
    upgrade_to_head(database_url)

    with TestClient(app) as test_client:
        yield test_client

    drop_db()
    _clear_caches()


def _clear_caches() -> None:
    from app.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    get_api_key_repository.cache_clear()
    get_api_key_token_service.cache_clear()
    container.get_auth_token_service.cache_clear()
    container.get_password_hasher.cache_clear()


def _register(client: TestClient, *, email: str = "dev@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Passw0rd123", "display_name": "Dev User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_api_key_returns_plaintext_once_and_lists_metadata_only(
    client: TestClient,
) -> None:
    session = _register(client)
    session_headers = _bearer(session["access_token"])

    created = client.post(
        "/api/keys", json={"name": "CI pipeline"}, headers=session_headers
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["api_key"].startswith("vfk_live_")
    assert body["name"] == "CI pipeline"
    assert body["token_prefix"] == body["api_key"][:16]

    listed = client.get("/api/keys", headers=session_headers)
    assert listed.status_code == 200
    keys = listed.json()
    assert len(keys) == 1
    assert keys[0]["id"] == body["id"]
    assert keys[0]["revoked"] is False
    # The secret and its hash must never be exposed after creation.
    assert "api_key" not in keys[0]
    assert "token_hash" not in keys[0]


def test_api_key_authenticates_on_legacy_and_versioned_surfaces(
    client: TestClient,
) -> None:
    session = _register(client, email="alice@example.com")
    created = client.post(
        "/api/keys", json={"name": "gateway"}, headers=_bearer(session["access_token"])
    )
    secret = created.json()["api_key"]

    via_header = client.get("/api/me", headers={"X-API-Key": secret})
    assert via_header.status_code == 200
    assert via_header.json()["email"] == "alice@example.com"

    via_bearer_v1 = client.get("/api/v1/me", headers=_bearer(secret))
    assert via_bearer_v1.status_code == 200
    assert via_bearer_v1.json()["email"] == "alice@example.com"


def test_session_token_still_works_on_versioned_surface(client: TestClient) -> None:
    session = _register(client)
    response = client.get("/api/v1/me", headers=_bearer(session["access_token"]))
    assert response.status_code == 200
    assert response.json()["email"] == "dev@example.com"


def test_invalid_api_key_is_rejected(client: TestClient) -> None:
    _register(client)
    response = client.get("/api/me", headers={"X-API-Key": "vfk_live_not_a_real_key"})
    assert response.status_code == 401


def test_revoked_api_key_stops_authenticating(client: TestClient) -> None:
    session = _register(client)
    session_headers = _bearer(session["access_token"])
    created = client.post("/api/keys", json={"name": "temp"}, headers=session_headers)
    key_id = created.json()["id"]
    secret = created.json()["api_key"]

    assert client.get("/api/me", headers={"X-API-Key": secret}).status_code == 200

    revoked = client.delete(f"/api/keys/{key_id}", headers=session_headers)
    assert revoked.status_code == 204

    assert client.get("/api/me", headers={"X-API-Key": secret}).status_code == 401

    listed = client.get("/api/keys", headers=session_headers)
    assert listed.json()[0]["revoked"] is True


def test_revoke_is_scoped_to_owner_and_hides_unknown_ids(client: TestClient) -> None:
    alice = _register(client, email="alice@example.com")
    bob = _register(client, email="bob@example.com")

    alice_key = client.post(
        "/api/keys", json={"name": "alice"}, headers=_bearer(alice["access_token"])
    ).json()

    # Bob cannot revoke Alice's key; it is indistinguishable from a missing key.
    cross = client.delete(
        f"/api/keys/{alice_key['id']}", headers=_bearer(bob["access_token"])
    )
    assert cross.status_code == 404

    missing = client.delete(
        "/api/keys/not-a-valid-uuid", headers=_bearer(alice["access_token"])
    )
    assert missing.status_code == 404

    # Alice's key remains usable after the failed cross-tenant revoke.
    assert (
        client.get("/api/me", headers={"X-API-Key": alice_key["api_key"]}).status_code
        == 200
    )


def test_key_management_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/keys").status_code == 401
    assert client.post("/api/keys", json={"name": "x"}).status_code == 401
