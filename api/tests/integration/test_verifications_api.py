from pathlib import Path
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
from app.entrypoints.api.dependencies.container import get_verification_repository
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
    get_verification_repository.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_verification_api_create_list_and_get(client: TestClient) -> None:
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
    assert list_response.status_code == 200
    listed_items = list_response.json()
    assert len(listed_items) == 1
    assert listed_items[0]["id"] == verification_id

    get_response = client.get(f"/api/verifications/{verification_id}")
    assert get_response.status_code == 200
    fetched_body = get_response.json()
    assert fetched_body["id"] == verification_id
    assert fetched_body["normalized_input"] == "https://verifiko.es/login"
    assert fetched_body["trace"]["total_signals"] == len(fetched_body["signals"])
    assert fetched_body["score_breakdown"]["base_score"] == 100.0
    assert fetched_body["risk_assessment"]["explanation"]["headline"]
    assert fetched_body["risk_assessment"]["explanation"]["analysis_trace"]


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
    assert created_body["risk_assessment"]["summary"].startswith("Se detectaron")
    assert created_body["risk_assessment"]["explanation"]["headline"].startswith("El motor produjo")

    verification_id = created_body["id"]

    get_response = client.get(
        f"/api/verifications/{verification_id}",
        headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"},
    )
    assert get_response.status_code == 200
    fetched_body = get_response.json()
    fetched_titles = {signal["title"] for signal in fetched_body["signals"]}
    assert "Cebo de credenciales en la URL" in fetched_titles
    assert fetched_body["risk_assessment"]["explanation"]["primary_factors"]

    list_response = client.get(
        "/api/verifications",
        headers={"Accept-Language": "es"},
    )
    assert list_response.status_code == 200
    listed_items = list_response.json()
    assert listed_items[0]["risk_assessment"]["summary"].startswith("Se detectaron")


def test_verification_api_returns_404_for_missing_verification(client: TestClient) -> None:
    response = client.get("/api/verifications/550e8400-e29b-41d4-a716-446655440099")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Verification not found: 550e8400-e29b-41d4-a716-446655440099"
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
