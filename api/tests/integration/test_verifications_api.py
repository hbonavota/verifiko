from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

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
    get_auth_token_service,
    get_create_verification_rate_limiter,
    get_google_identity_verifier,
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


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "verifiko-api.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"

    monkeypatch.setenv("DATABASE_URL", database_url)

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    container.get_create_verification_rate_limiter.cache_clear()
    container.get_user_quota_policy.cache_clear()
    container.get_authenticated_verification_rate_limiter.cache_clear()
    container.get_auth_token_service.cache_clear()
    container.get_google_identity_verifier.cache_clear()
    container.get_redirect_signal_analyzer.cache_clear()
    container.get_reputation_signal_analyzer.cache_clear()
    container.get_infrastructure_signal_analyzer.cache_clear()
    container.get_resolved_destination_signal_analyzer.cache_clear()

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
    container.get_auth_token_service.cache_clear()
    container.get_google_identity_verifier.cache_clear()
    get_verification_repository.cache_clear()
    get_user_repository.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_verification_api_create_disables_public_list_and_get(client: TestClient) -> None:
    create_response = client.post(
        "/api/verifications",
        json={
            "url": "verifiko.es/login",
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
    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "Public verification history is disabled on this endpoint."
    )

    get_response = client.get(f"/api/verifications/{verification_id}")
    assert get_response.status_code == 401
    assert get_response.json()["detail"] == (
        "Authentication is required for this endpoint."
    )
    assert create_response.headers["x-content-type-options"] == "nosniff"
    assert create_response.headers["x-frame-options"] == "DENY"
    assert create_response.headers["referrer-policy"] == "no-referrer"
    assert create_response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )


def test_verification_api_redacts_sensitive_url_parts_before_persistence_and_exposure(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/verifications",
        json={
            "url": (
                "https://user:secret@secure-paypal-login.example.xyz/verify"
                "?token=abc123&redirect=https://example.org#otp=456789"
            ),
        },
    )

    assert create_response.status_code == 201
    created_body = create_response.json()
    assert created_body["original_input"] == "https://secure-paypal-login.example.xyz/verify"
    assert created_body["normalized_input"] == "https://secure-paypal-login.example.xyz/verify"

    repository = get_verification_repository()
    stored = repository.list(limit=1)[0]
    assert stored.original_input == "https://secure-paypal-login.example.xyz/verify"
    assert stored.normalized_input.normalized == "https://secure-paypal-login.example.xyz/verify"


def test_verification_api_preserves_clean_urls_without_sensitive_parts(client: TestClient) -> None:
    create_response = client.post(
        "/api/verifications",
        json={"url": "verifiko.es/login"},
    )

    assert create_response.status_code == 201
    created_body = create_response.json()
    assert created_body["original_input"] == "verifiko.es/login"
    assert created_body["normalized_input"] == "https://verifiko.es/login"


def test_verification_api_rate_limits_anonymous_create_requests(client: TestClient) -> None:
    limiter = get_create_verification_rate_limiter()
    limiter.reset()
    limiter.daily_limit = 2
    limiter.current_time_provider = lambda: datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)

    first = client.post("/api/verifications", json={"url": "https://example.org"})
    second = client.post("/api/verifications", json={"url": "https://example.net"})
    third = client.post("/api/verifications", json={"url": "https://example.com"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 429
    assert third.json()["detail"] == (
        "The anonymous verification limit for today has been reached. Please try again after midnight UTC or sign in."
    )
    assert third.headers["retry-after"] == "43200"

    limiter.reset()
    limiter.daily_limit = get_settings().anonymous_daily_verification_limit


def test_verification_api_resets_anonymous_daily_limit_at_utc_midnight(client: TestClient) -> None:
    limiter = get_create_verification_rate_limiter()
    limiter.reset()
    current_time = datetime(2026, 3, 28, 23, 59, 50, tzinfo=timezone.utc)
    limiter.daily_limit = 1
    limiter.current_time_provider = lambda: current_time

    first = client.post("/api/verifications", json={"url": "https://example.org"})
    blocked = client.post("/api/verifications", json={"url": "https://example.net"})

    assert first.status_code == 201
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "10"

    current_time = datetime(2026, 3, 29, 0, 0, 5, tzinfo=timezone.utc)
    allowed_after_reset = client.post("/api/verifications", json={"url": "https://example.com"})

    assert allowed_after_reset.status_code == 201

    limiter.reset()
    limiter.daily_limit = get_settings().anonymous_daily_verification_limit


def test_verification_api_rejects_overlong_url_input(client: TestClient) -> None:
    response = client.post(
        "/api/verifications",
        json={"url": f"https://example.org/{'a' * 5000}"},
    )

    assert response.status_code == 422


def test_health_endpoint_applies_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )


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


def test_verification_api_localizes_backend_generated_text_with_accept_language(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/verifications",
        json={
            "url": "http://paypal-login-security-check.example.xyz/verify?redirect=https://example.org",
        },
        headers={"Accept-Language": "es"},
    )

    assert create_response.status_code == 201
    created_body = create_response.json()
    signal_titles = {signal["title"] for signal in created_body["signals"]}
    assert "Cebo de credenciales en la URL" in signal_titles
    assert created_body["risk_assessment"]["summary"].startswith(
        "Principal riesgo:"
    )
    assert created_body["risk_assessment"]["explanation"]["headline"].startswith("El motor produjo")

    list_response = client.get(
        "/api/verifications",
        headers={"Accept-Language": "es"},
    )
    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "El historial público de verificaciones está deshabilitado en este endpoint."
    )


def test_verification_api_returns_404_for_missing_verification(client: TestClient) -> None:
    response = client.get("/api/verifications/550e8400-e29b-41d4-a716-446655440099")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication is required for this endpoint."
    )


def test_verification_api_localizes_known_error_details_with_accept_language(
    client: TestClient,
) -> None:
    signals_response = client.post(
        "/api/verifications",
        json={
            "url": "https://openai.com",
            "signals": [
                {
                    "signal_type": "blacklist_match",
                    "category": "content_behavior",
                    "severity": "CRITICAL",
                    "confidence": 99,
                    "title": "Injected blacklist hit",
                    "description": "Injected by client.",
                    "source": "client",
                }
            ],
        },
        headers={"Accept-Language": "es"},
    )

    assert signals_response.status_code == 422
    assert signals_response.json()["detail"] == (
        "Las señales proporcionadas por el cliente no se aceptan en este endpoint."
    )

    local_response = client.post(
        "/api/verifications",
        json={"url": "https://localhost/login"},
        headers={"Accept-Language": "es"},
    )

    assert local_response.status_code == 422
    assert local_response.json()["detail"] == (
        "El destino saliente es un hostname local o de uso especial y fue bloqueado."
    )

    not_found_response = client.get(
        "/api/verifications/550e8400-e29b-41d4-a716-446655440099",
        headers={"Accept-Language": "es"},
    )

    assert not_found_response.status_code == 401
    assert not_found_response.json()["detail"] == (
        "Se requiere autenticación para este endpoint."
    )

    invalid_id_response = client.get(
        "/api/verifications/not-a-verification-id",
        headers={"Accept-Language": "es"},
    )

    assert invalid_id_response.status_code == 401
    assert invalid_id_response.json()["detail"] == (
        "Se requiere autenticación para este endpoint."
    )


def test_verification_api_rejects_client_supplied_signals(client: TestClient) -> None:
    response = client.post(
        "/api/verifications",
        json={
            "url": "https://openai.com",
            "signals": [
                {
                    "signal_type": "blacklist_match",
                    "category": "content_behavior",
                    "severity": "CRITICAL",
                    "confidence": 99,
                    "title": "Injected blacklist hit",
                    "description": "Injected by client.",
                    "source": "client",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Client-supplied signals are not accepted on this endpoint."
    )


def test_verification_api_rejects_unsafe_local_targets(client: TestClient) -> None:
    response = client.post(
        "/api/verifications",
        json={
            "url": "https://localhost/login",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Outbound target is a local or special-use hostname and was blocked."
    )


def test_verification_api_rejects_single_label_targets(client: TestClient) -> None:
    response = client.post(
        "/api/verifications",
        json={
            "url": "A",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Outbound target uses a single-label hostname and was blocked."
    )
