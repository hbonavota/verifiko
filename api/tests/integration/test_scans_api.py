from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.redirect_resolver import RedirectResolution, RedirectResolverPort
from app.application.ports.reputation_lookup import ReputationLookupPort
from app.application.services.infrastructure_signal_analyzer import InfrastructureSignalAnalyzer
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
import app.entrypoints.api.dependencies.container as container
from app.entrypoints.api.dependencies.container import (
    get_user_repository,
    get_verification_repository,
)
from app.entrypoints.api.main import app
from app.infrastructure.external_services.outbound_target_guard import UnsafeOutboundTargetError
from app.infrastructure.jobs.scan_dispatchers import SynchronousVerificationJobDispatcher
from app.infrastructure.persistence.database import drop_db, get_engine, get_session_factory
from tests.integration.alembic_helpers import upgrade_to_head


class NoopRedirectResolver(RedirectResolverPort):
    def resolve(self, url: str) -> RedirectResolution:
        return RedirectResolution(final_url=url, hops=(), provider_name="stub-redirect")


class NoopReputationLookup(ReputationLookupPort):
    def lookup(self, hostname: str):
        return None


class NoopInfrastructureLookup(InfrastructureLookupPort):
    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        return InfrastructureProfile(
            queried_host=hostname,
            provider_name="stub-infrastructure",
            resolved_addresses=(ResolvedAddress(ip_address="203.0.113.10"),),
        )


def _test_public_target_validator(url: str) -> None:
    hostname = (urlsplit(url).hostname or "").lower()
    if hostname == "localhost" or (hostname and "." not in hostname):
        raise UnsafeOutboundTargetError("blocked")


_SCAN_CACHES = (
    "get_verification_job_store",
    "get_verification_scan_processor",
    "get_verification_scan_dispatcher",
    "get_scan_webhook_notifier",
)


class _NoopWebhookNotifier:
    def notify(self, job) -> None:  # keep integration tests network-free
        return None


def _clear_scan_caches() -> None:
    for name in _SCAN_CACHES:
        clear = getattr(getattr(container, name), "cache_clear", None)
        if clear is not None:
            clear()


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'verifiko-scans.sqlite3'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "test-auth-secret")

    from app.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    container.get_auth_token_service.cache_clear()
    container.get_password_hasher.cache_clear()
    container.get_api_key_repository.cache_clear()
    container.get_redirect_signal_analyzer.cache_clear()
    container.get_reputation_signal_analyzer.cache_clear()
    container.get_infrastructure_signal_analyzer.cache_clear()
    _clear_scan_caches()

    monkeypatch.setattr(
        container,
        "get_redirect_signal_analyzer",
        lambda: RedirectSignalAnalyzer(redirect_resolver=NoopRedirectResolver()),
    )
    monkeypatch.setattr(
        container,
        "get_reputation_signal_analyzer",
        lambda: ReputationSignalAnalyzer(reputation_lookup=NoopReputationLookup()),
    )
    monkeypatch.setattr(
        container,
        "get_infrastructure_signal_analyzer",
        lambda: InfrastructureSignalAnalyzer(infrastructure_lookup=NoopInfrastructureLookup()),
    )
    monkeypatch.setattr(container, "assert_safe_outbound_url", _test_public_target_validator)
    monkeypatch.setattr(container, "get_scan_webhook_notifier", lambda: _NoopWebhookNotifier())
    # Deterministic: process the scan inline so a poll immediately after submit
    # observes the completed result.
    monkeypatch.setattr(
        container,
        "get_verification_scan_dispatcher",
        lambda: SynchronousVerificationJobDispatcher(container.get_verification_scan_processor()),
    )

    upgrade_to_head(database_url)
    with TestClient(app) as test_client:
        yield test_client

    drop_db()
    _clear_scan_caches()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def _register(client: TestClient, email: str = "dev@example.com") -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Passw0rd123", "display_name": "Dev"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_submit_returns_202_and_poll_reaches_completed(client: TestClient) -> None:
    headers = _register(client)

    submitted = client.post("/api/v1/scans", json={"url": "https://example.org"}, headers=headers)
    assert submitted.status_code == 202
    body = submitted.json()
    assert body["status"] == "queued"
    scan_id = body["scan_id"]

    polled = client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert polled.status_code == 200
    result = polled.json()
    assert result["status"] == "completed"
    assert result["result_verification_id"]
    assert result["result"] is not None
    assert result["result"]["risk_assessment"]["risk_level"]


def test_batch_creates_multiple_scans(client: TestClient) -> None:
    headers = _register(client)

    response = client.post(
        "/api/v1/scans/batch",
        json={"urls": ["https://example.org", "https://example.net"]},
        headers=headers,
    )
    assert response.status_code == 202
    scans = response.json()["scans"]
    assert len(scans) == 2

    for scan in scans:
        polled = client.get(f"/api/v1/scans/{scan['scan_id']}", headers=headers)
        assert polled.status_code == 200
        assert polled.json()["status"] == "completed"


def test_scan_is_owner_scoped(client: TestClient) -> None:
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")

    scan_id = client.post(
        "/api/v1/scans", json={"url": "https://example.org"}, headers=owner
    ).json()["scan_id"]

    assert client.get(f"/api/v1/scans/{scan_id}", headers=other).status_code == 404
    assert client.get(f"/api/v1/scans/{scan_id}", headers=owner).status_code == 200


def test_scan_endpoints_require_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/scans", json={"url": "https://example.org"}).status_code == 401
    assert client.get("/api/v1/scans/anything").status_code == 401


def test_submit_rejects_invalid_webhook_url(client: TestClient) -> None:
    headers = _register(client)
    response = client.post(
        "/api/v1/scans",
        json={"url": "https://example.org", "webhook_url": "ftp://not-http.example"},
        headers=headers,
    )
    assert response.status_code == 422


def test_submit_accepts_valid_webhook_url(client: TestClient) -> None:
    headers = _register(client)
    response = client.post(
        "/api/v1/scans",
        json={"url": "https://example.org", "webhook_url": "https://hooks.example/cb"},
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


class _FakeScreenshotStore:
    def store(self, image_bytes: bytes, *, content_type: str = "image/png") -> str:
        return "screenshots/x.png"

    def presigned_url(self, ref: str, *, expires_in: int = 3600) -> str:
        return f"https://signed.example/{ref}?exp={expires_in}"


def test_scan_result_exposes_presigned_screenshot_url(client: TestClient) -> None:
    from app.entrypoints.api.dependencies.container import get_screenshot_store

    app.dependency_overrides[get_screenshot_store] = lambda: _FakeScreenshotStore()
    try:
        headers = _register(client)
        scan_id = client.post(
            "/api/v1/scans", json={"url": "https://example.org"}, headers=headers
        ).json()["scan_id"]

        # Seed a screenshot reference onto the completed job. This also exercises
        # migration 0009: the write fails if the screenshot_ref column is absent.
        job_store = container.get_verification_job_store()
        job = job_store.get(scan_id)
        assert job is not None
        job.screenshot_ref = "screenshots/x.png"
        job_store.save(job)

        polled = client.get(f"/api/v1/scans/{scan_id}", headers=headers).json()
        expected = "https://signed.example/screenshots/x.png?exp=3600"
        assert polled["screenshot_url"] == expected
        assert polled["result"]["screenshot_url"] == expected
    finally:
        app.dependency_overrides.pop(get_screenshot_store, None)


def test_scan_without_screenshot_has_null_screenshot_url(client: TestClient) -> None:
    headers = _register(client)
    scan_id = client.post(
        "/api/v1/scans", json={"url": "https://example.org"}, headers=headers
    ).json()["scan_id"]

    polled = client.get(f"/api/v1/scans/{scan_id}", headers=headers).json()
    assert polled["screenshot_url"] is None
    assert polled["result"]["screenshot_url"] is None


def test_invalid_url_scan_reports_failed(client: TestClient) -> None:
    headers = _register(client)
    scan_id = client.post(
        "/api/v1/scans", json={"url": "ftp://not-supported.example"}, headers=headers
    ).json()["scan_id"]

    polled = client.get(f"/api/v1/scans/{scan_id}", headers=headers).json()
    assert polled["status"] == "failed"
    assert polled["error"]
    assert polled["result"] is None
