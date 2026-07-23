from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.application.ports.email_sender import EmailMessage, EmailSenderPort
import app.entrypoints.api.dependencies.container as container
from app.entrypoints.api.dependencies.container import (
    get_user_repository,
    get_verification_repository,
)
from app.entrypoints.api.main import app
from app.infrastructure.persistence.database import drop_db, get_engine, get_session_factory
from tests.integration.alembic_helpers import upgrade_to_head

_SENT: list[EmailMessage] = []


class _CapturingSender(EmailSenderPort):
    def send(self, message: EmailMessage) -> None:
        _SENT.append(message)


_MAGIC_CACHES = (
    "get_magic_link_store",
    "get_email_sender",
    "get_magic_link_request_rate_limiter",
)


def _clear_magic_caches() -> None:
    for name in _MAGIC_CACHES:
        clear = getattr(getattr(container, name), "cache_clear", None)
        if clear is not None:
            clear()


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'verifiko-magic.sqlite3'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "test-auth-secret")
    monkeypatch.setenv("MAGIC_LINK_REQUEST_LIMIT_REQUESTS", "2")

    from app.infrastructure.config.settings import get_settings

    _SENT.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    container.get_auth_token_service.cache_clear()
    _clear_magic_caches()

    monkeypatch.setattr(container, "get_email_sender", lambda: _CapturingSender())

    upgrade_to_head(database_url)
    with TestClient(app) as test_client:
        yield test_client

    drop_db()
    _clear_magic_caches()
    get_user_repository.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def _token_from_last_email() -> str:
    return _SENT[-1].text.split("token=")[1].split()[0]


def test_magic_link_request_consume_and_authenticated_access(client: TestClient) -> None:
    requested = client.post("/api/v1/auth/magic-link/request", json={"email": "new@example.com"})
    assert requested.status_code == 202
    assert requested.json()["status"] == "sent"
    assert len(_SENT) == 1
    assert _SENT[0].to == "new@example.com"

    token = _token_from_last_email()
    consumed = client.post("/api/v1/auth/magic-link/consume", json={"token": token})
    assert consumed.status_code == 200
    body = consumed.json()
    assert body["token_type"] == "Bearer"
    assert body["user"]["email"] == "new@example.com"

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_magic_link_token_is_single_use(client: TestClient) -> None:
    client.post("/api/v1/auth/magic-link/request", json={"email": "once@example.com"})
    token = _token_from_last_email()

    assert client.post("/api/v1/auth/magic-link/consume", json={"token": token}).status_code == 200
    assert client.post("/api/v1/auth/magic-link/consume", json={"token": token}).status_code == 401


def test_magic_link_rejects_unknown_token(client: TestClient) -> None:
    response = client.post("/api/v1/auth/magic-link/consume", json={"token": "not-a-real-token"})
    assert response.status_code == 401


def test_magic_link_request_is_rate_limited(client: TestClient) -> None:
    # Limit set to 2 per window via env in the fixture.
    assert client.post("/api/v1/auth/magic-link/request", json={"email": "a@example.com"}).status_code == 202
    assert client.post("/api/v1/auth/magic-link/request", json={"email": "b@example.com"}).status_code == 202
    limited = client.post("/api/v1/auth/magic-link/request", json={"email": "c@example.com"})
    assert limited.status_code == 429
    assert "retry-after" in {k.lower() for k in limited.headers}


def test_magic_link_request_validates_email(client: TestClient) -> None:
    assert client.post("/api/v1/auth/magic-link/request", json={"email": "not-an-email"}).status_code == 422
