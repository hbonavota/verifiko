from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

from app.application.ports.google_identity_verifier import (
    GoogleIdentity,
    GoogleIdentityVerificationError,
)
from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.redirect_resolver import (
    RedirectResolution,
    RedirectResolverPort,
)
from app.application.ports.reputation_lookup import ReputationLookupPort
from app.application.services.infrastructure_signal_analyzer import InfrastructureSignalAnalyzer
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
import app.entrypoints.api.dependencies.container as container
from app.entrypoints.api.dependencies.container import (
    get_create_verification_rate_limiter,
    get_user_repository,
    get_verification_repository,
)
from app.entrypoints.api.main import app
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external_services.outbound_target_guard import UnsafeOutboundTargetError
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


class FakeGoogleIdentityVerifier:
    def verify(self, id_token: str) -> GoogleIdentity:
        if id_token == "valid-alice":
            return GoogleIdentity(
                subject="google-sub-alice",
                email="alice@example.com",
                display_name="Alice Example",
                avatar_url="https://example.com/alice.png",
            )
        if id_token == "valid-bob":
            return GoogleIdentity(
                subject="google-sub-bob",
                email="bob@example.com",
                display_name="Bob Example",
                avatar_url=None,
            )
        raise GoogleIdentityVerificationError("Google identity token could not be verified.")


def _test_public_target_validator(url: str) -> None:
    hostname = (urlsplit(url).hostname or "").lower()
    if hostname == "localhost":
        raise UnsafeOutboundTargetError(
            "Outbound target is a local or special-use hostname and was blocked."
        )
    if hostname and "." not in hostname:
        raise UnsafeOutboundTargetError(
            "Outbound target uses a single-label hostname and was blocked."
        )


def _clear_cache_if_present(target) -> None:
    cache_clear = getattr(target, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "verifiko-auth.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "test-auth-secret")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    container.get_create_verification_rate_limiter.cache_clear()
    container.get_auth_token_service.cache_clear()
    container.get_google_identity_verifier.cache_clear()
    container.get_redirect_signal_analyzer.cache_clear()
    container.get_reputation_signal_analyzer.cache_clear()
    container.get_infrastructure_signal_analyzer.cache_clear()
    container.get_resolved_destination_signal_analyzer.cache_clear()

    monkeypatch.setattr(
        container,
        "get_google_identity_verifier",
        lambda: FakeGoogleIdentityVerifier(),
    )
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

    upgrade_to_head(database_url)

    with TestClient(app) as test_client:
        yield test_client

    drop_db()
    container.get_create_verification_rate_limiter.cache_clear()
    container.get_auth_token_service.cache_clear()
    _clear_cache_if_present(container.get_google_identity_verifier)
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def _login(client: TestClient, id_token: str) -> dict[str, str]:
    response = client.post("/api/auth/google", json={"id_token": id_token})
    assert response.status_code == 200
    return response.json()


def _authorization_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_google_login_success_returns_backend_session_and_user(client: TestClient) -> None:
    response = client.post("/api/auth/google", json={"id_token": "valid-alice"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["display_name"] == "Alice Example"


def test_google_login_rejects_invalid_identity_token(client: TestClient) -> None:
    response = client.post("/api/auth/google", json={"id_token": "invalid-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Google identity token could not be verified."


def test_current_user_resolution_requires_valid_bearer_token(client: TestClient) -> None:
    session = _login(client, "valid-alice")

    success = client.get("/api/me", headers=_authorization_header(session["access_token"]))
    assert success.status_code == 200
    assert success.json()["email"] == "alice@example.com"

    invalid = client.get("/api/me", headers=_authorization_header("not-a-valid-token"))
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Authentication token is invalid or expired."


def test_authenticated_create_assigns_owner_while_anonymous_create_remains_allowed(
    client: TestClient,
) -> None:
    session = _login(client, "valid-alice")

    owned_response = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(session["access_token"]),
    )
    anonymous_response = client.post(
        "/api/verifications",
        json={"url": "https://example.net"},
    )

    assert owned_response.status_code == 201
    assert anonymous_response.status_code == 201

    user_repository = get_user_repository()
    owner = user_repository.get_by_email("alice@example.com")
    assert owner is not None

    verification_repository = get_verification_repository()
    owned = verification_repository.list_for_owner(owner.id, limit=10)
    assert len(owned) == 1
    assert owned[0].id.value.hex.replace("-", "") != ""

    all_verifications = verification_repository.list(limit=10)
    assert any(item.user_id is None for item in all_verifications)


def test_owner_can_retrieve_own_verification_but_non_owner_and_anonymous_cannot(
    client: TestClient,
) -> None:
    alice = _login(client, "valid-alice")
    bob = _login(client, "valid-bob")

    created = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(alice["access_token"]),
    )
    assert created.status_code == 201
    verification_id = created.json()["id"]

    owner_response = client.get(
        f"/api/verifications/{verification_id}",
        headers=_authorization_header(alice["access_token"]),
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["id"] == verification_id

    non_owner_response = client.get(
        f"/api/verifications/{verification_id}",
        headers=_authorization_header(bob["access_token"]),
    )
    assert non_owner_response.status_code == 404

    anonymous_response = client.get(f"/api/verifications/{verification_id}")
    assert anonymous_response.status_code == 401


def test_my_verifications_returns_only_owned_records(client: TestClient) -> None:
    alice = _login(client, "valid-alice")
    bob = _login(client, "valid-bob")

    alice_first = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(alice["access_token"]),
    )
    alice_second = client.post(
        "/api/verifications",
        json={"url": "https://example.net"},
        headers=_authorization_header(alice["access_token"]),
    )
    bob_only = client.post(
        "/api/verifications",
        json={"url": "https://example.com"},
        headers=_authorization_header(bob["access_token"]),
    )

    assert alice_first.status_code == 201
    assert alice_second.status_code == 201
    assert bob_only.status_code == 201

    alice_list = client.get(
        "/api/me/verifications?limit=10",
        headers=_authorization_header(alice["access_token"]),
    )
    assert alice_list.status_code == 200
    alice_ids = {item["id"] for item in alice_list.json()}
    assert alice_ids == {alice_first.json()["id"], alice_second.json()["id"]}

    bob_list = client.get(
        "/api/me/verifications?limit=10",
        headers=_authorization_header(bob["access_token"]),
    )
    assert bob_list.status_code == 200
    bob_ids = {item["id"] for item in bob_list.json()}
    assert bob_ids == {bob_only.json()["id"]}


def test_authenticated_create_is_not_subject_to_anonymous_rate_limit(client: TestClient) -> None:
    session = _login(client, "valid-alice")
    limiter = get_create_verification_rate_limiter()
    limiter.reset()
    limiter.daily_limit = 1

    first = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(session["access_token"]),
    )
    second = client.post(
        "/api/verifications",
        json={"url": "https://example.net"},
        headers=_authorization_header(session["access_token"]),
    )

    assert first.status_code == 201
    assert second.status_code == 201

    limiter.reset()
    limiter.daily_limit = get_settings().anonymous_daily_verification_limit
