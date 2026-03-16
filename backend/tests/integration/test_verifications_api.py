from fastapi.testclient import TestClient

from app.entrypoints.api.dependencies.container import get_verification_repository
from app.entrypoints.api.main import app


def test_verification_api_create_list_and_get() -> None:
    repository = get_verification_repository()
    repository.clear()

    client = TestClient(app)

    create_response = client.post(
        "/api/verifications",
        json={
            "url": "verifiko.es/login",
            "signals": [
                {
                    "signal_type": "BRAND_IMPERSONATION",
                    "category": "CONTENT_BEHAVIOR",
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


def test_verification_api_returns_404_for_missing_verification() -> None:
    repository = get_verification_repository()
    repository.clear()

    client = TestClient(app)

    response = client.get("/api/verifications/550e8400-e29b-41d4-a716-446655440099")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Verification not found: 550e8400-e29b-41d4-a716-446655440099"
    )
