from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

from app.application.ports.google_identity_verifier import (
    GoogleIdentity,
    GoogleIdentityVerificationError,
)
from app.domain.enums.user_plan import UserPlan
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
    container.get_user_quota_policy.cache_clear()
    container.get_authenticated_verification_rate_limiter.cache_clear()
    container.get_quota_status_service.cache_clear()
    container.get_auth_token_service.cache_clear()
    container.get_password_hasher.cache_clear()
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
    container.get_user_quota_policy.cache_clear()
    container.get_authenticated_verification_rate_limiter.cache_clear()
    container.get_quota_status_service.cache_clear()
    container.get_auth_token_service.cache_clear()
    container.get_password_hasher.cache_clear()
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


def _register_local(
    client: TestClient,
    *,
    email: str = "local@example.com",
    password: str = "Passw0rd123",
    display_name: str = "Local User",
):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )


def _login_local(
    client: TestClient,
    *,
    email: str = "local@example.com",
    password: str = "Passw0rd123",
):
    return client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


def test_google_login_success_returns_backend_session_and_user(client: TestClient) -> None:
    response = client.post("/api/auth/google", json={"id_token": "valid-alice"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["display_name"] == "Alice Example"
    assert body["user"]["plan"] == "FREE"


def test_local_registration_success_returns_backend_session_and_user(client: TestClient) -> None:
    response = _register_local(client)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "local@example.com"
    assert body["user"]["display_name"] == "Local User"
    assert body["user"]["plan"] == "FREE"


def test_local_registration_rejects_duplicate_email(client: TestClient) -> None:
    first = _register_local(client)
    duplicate = _register_local(client)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An account already exists for this email."


def test_local_registration_validates_password_policy(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "local@example.com",
            "password": "short",
            "display_name": "Local User",
        },
    )

    assert response.status_code == 422


def test_local_login_success_returns_backend_session_and_current_user(client: TestClient) -> None:
    _register_local(client)

    response = _login_local(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["user"]["email"] == "local@example.com"

    current_user = client.get("/api/me", headers=_authorization_header(body["access_token"]))
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "local@example.com"


def test_local_login_rejects_invalid_credentials_without_user_enumeration(client: TestClient) -> None:
    _register_local(client)

    wrong_password = _login_local(client, password="WrongPass123")
    missing_user = _login_local(client, email="missing@example.com")

    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"] == "Email or password is incorrect."
    assert missing_user.status_code == 401
    assert missing_user.json()["detail"] == "Email or password is incorrect."


def test_google_login_reuses_existing_local_user_by_email(client: TestClient) -> None:
    local_session = _register_local(
        client,
        email="alice@example.com",
        display_name="Alice Local",
    )
    google_session = _login(client, "valid-alice")

    assert local_session.status_code == 201
    assert google_session["user"]["email"] == "alice@example.com"
    assert google_session["user"]["id"] == local_session.json()["user"]["id"]


def test_google_login_rejects_invalid_identity_token(client: TestClient) -> None:
    response = client.post("/api/auth/google", json={"id_token": "invalid-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Google identity token could not be verified."


def test_current_user_resolution_requires_valid_bearer_token(client: TestClient) -> None:
    session = _login(client, "valid-alice")

    success = client.get("/api/me", headers=_authorization_header(session["access_token"]))
    assert success.status_code == 200
    assert success.json()["email"] == "alice@example.com"
    assert success.json()["plan"] == "FREE"

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


def test_authenticated_user_hits_daily_limit(client: TestClient) -> None:
    session = _login(client, "valid-alice")
    policy = container.get_user_quota_policy()
    limiter = container.get_authenticated_verification_rate_limiter()
    policy.free_daily_limit = 2
    limiter.current_time_provider = lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
    limiter.reset()

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
    third = client.post(
        "/api/verifications",
        json={"url": "https://example.com"},
        headers=_authorization_header(session["access_token"]),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 429
    assert third.json()["detail"] == "You’ve reached your daily verification limit. Upgrade to continue."
    assert third.headers["retry-after"] == "43200"

    policy.free_daily_limit = get_settings().free_authenticated_daily_verification_limit
    limiter.reset()


def test_limit_resets_next_day(client: TestClient) -> None:
    session = _login(client, "valid-alice")
    policy = container.get_user_quota_policy()
    limiter = container.get_authenticated_verification_rate_limiter()
    current_time = datetime(2026, 3, 28, 23, 59, 50, tzinfo=timezone.utc)
    policy.free_daily_limit = 1
    limiter.current_time_provider = lambda: current_time
    limiter.reset()

    first = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(session["access_token"]),
    )
    blocked = client.post(
        "/api/verifications",
        json={"url": "https://example.net"},
        headers=_authorization_header(session["access_token"]),
    )

    assert first.status_code == 201
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "10"

    current_time = datetime(2026, 3, 29, 0, 0, 5, tzinfo=timezone.utc)
    allowed_after_reset = client.post(
        "/api/verifications",
        json={"url": "https://example.com"},
        headers=_authorization_header(session["access_token"]),
    )

    assert allowed_after_reset.status_code == 201

    policy.free_daily_limit = get_settings().free_authenticated_daily_verification_limit
    limiter.reset()


def test_different_users_have_isolated_quotas(client: TestClient) -> None:
    alice = _login(client, "valid-alice")
    bob = _login(client, "valid-bob")
    policy = container.get_user_quota_policy()
    limiter = container.get_authenticated_verification_rate_limiter()
    policy.free_daily_limit = 1
    limiter.current_time_provider = lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
    limiter.reset()

    alice_first = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(alice["access_token"]),
    )
    alice_blocked = client.post(
        "/api/verifications",
        json={"url": "https://example.net"},
        headers=_authorization_header(alice["access_token"]),
    )
    bob_first = client.post(
        "/api/verifications",
        json={"url": "https://example.com"},
        headers=_authorization_header(bob["access_token"]),
    )

    assert alice_first.status_code == 201
    assert alice_blocked.status_code == 429
    assert bob_first.status_code == 201

    policy.free_daily_limit = get_settings().free_authenticated_daily_verification_limit
    limiter.reset()


def test_pro_user_has_higher_limit(client: TestClient) -> None:
    session = _login(client, "valid-alice")
    user_repository = get_user_repository()
    user = user_repository.get_by_email("alice@example.com")
    assert user is not None
    user.assign_plan(UserPlan.PRO)
    user_repository.save(user)

    policy = container.get_user_quota_policy()
    limiter = container.get_authenticated_verification_rate_limiter()
    policy.free_daily_limit = 1
    policy.pro_daily_limit = 2
    limiter.current_time_provider = lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
    limiter.reset()

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
    third = client.post(
        "/api/verifications",
        json={"url": "https://example.com"},
        headers=_authorization_header(session["access_token"]),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 429

    policy.free_daily_limit = get_settings().free_authenticated_daily_verification_limit
    policy.pro_daily_limit = get_settings().pro_authenticated_daily_verification_limit
    limiter.reset()


def test_authenticated_quota_status_reports_remaining_usage_truthfully(client: TestClient) -> None:
    session = _login(client, "valid-alice")
    limiter = container.get_authenticated_verification_rate_limiter()
    limiter.reset()
    limiter.current_time_provider = lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)

    created = client.post(
        "/api/verifications",
        json={"url": "https://example.org"},
        headers=_authorization_header(session["access_token"]),
    )
    status_response = client.get(
        "/api/verifications/quota-status",
        headers=_authorization_header(session["access_token"]),
    )

    assert created.status_code == 201
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["subject_type"] == "USER"
    assert body["is_authenticated"] is True
    assert body["plan"] == "FREE"
    assert body["daily_limit"] == 10
    assert body["used_today"] == 1
    assert body["remaining_today"] == 9
    assert body["reset_in_seconds"] == 43200
    assert body["reset_at_utc"] == "2026-03-29T00:00:00Z"
    assert body["blocked"] is False

    limiter.reset()


def test_pro_quota_status_reports_paid_limit_truthfully(client: TestClient) -> None:
    session = _login(client, "valid-alice")
    user_repository = get_user_repository()
    user = user_repository.get_by_email("alice@example.com")
    assert user is not None
    user.assign_plan(UserPlan.PRO)
    user_repository.save(user)

    limiter = container.get_authenticated_verification_rate_limiter()
    limiter.reset()
    limiter.current_time_provider = lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)

    status_response = client.get(
        "/api/verifications/quota-status",
        headers=_authorization_header(session["access_token"]),
    )

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["subject_type"] == "USER"
    assert body["plan"] == "PRO"
    assert body["daily_limit"] == 200
    assert body["used_today"] == 0
    assert body["remaining_today"] == 200
    assert body["blocked"] is False

    limiter.reset()
