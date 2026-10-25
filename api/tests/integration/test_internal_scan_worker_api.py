import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

import app.entrypoints.api.dependencies.container as container
from app.entrypoints.api.main import app
from app.infrastructure.security.qstash_signature_verifier import (
    QStashSignatureVerifier,
)

_SIGNING_KEY = "worker-signing-key"


def _seg(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _token(body: bytes, key: str = _SIGNING_KEY) -> str:
    now = int(time.time())
    payload = {
        "iss": "Upstash",
        "exp": now + 300,
        "nbf": now - 10,
        "body": base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode("ascii"),
    }
    signing_input = f"{_seg({'alg': 'HS256', 'typ': 'JWT'})}.{_seg(payload)}"
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(
                key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
            ).digest()
        )
        .rstrip(b"=")
        .decode("ascii")
    )
    return f"{signing_input}.{signature}"


class _RecordingProcessor:
    def __init__(self) -> None:
        self.processed: list[str] = []

    def process(self, job_id: str) -> None:
        self.processed.append(job_id)


@pytest.fixture()
def worker_client():
    processor = _RecordingProcessor()
    app.dependency_overrides[container.get_qstash_signature_verifier] = (
        lambda: QStashSignatureVerifier(_SIGNING_KEY)
    )
    app.dependency_overrides[container.get_verification_scan_processor] = (
        lambda: processor
    )
    try:
        with TestClient(app) as client:
            yield client, processor
    finally:
        app.dependency_overrides.clear()


def test_valid_signed_request_processes_job(worker_client) -> None:
    client, processor = worker_client
    body = json.dumps({"job_id": "job-abc"}).encode("utf-8")

    response = client.post(
        "/api/v1/scans/process",
        content=body,
        headers={"Upstash-Signature": _token(body), "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "processed", "job_id": "job-abc"}
    assert processor.processed == ["job-abc"]


def test_missing_signature_is_rejected(worker_client) -> None:
    client, processor = worker_client
    body = json.dumps({"job_id": "job-abc"}).encode("utf-8")

    response = client.post(
        "/api/v1/scans/process",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401
    assert processor.processed == []


def test_wrong_key_signature_is_rejected(worker_client) -> None:
    client, processor = worker_client
    body = json.dumps({"job_id": "job-abc"}).encode("utf-8")

    response = client.post(
        "/api/v1/scans/process",
        content=body,
        headers={"Upstash-Signature": _token(body, key="attacker-key")},
    )

    assert response.status_code == 401
    assert processor.processed == []


def test_tampered_body_is_rejected(worker_client) -> None:
    client, processor = worker_client
    signed_body = json.dumps({"job_id": "job-abc"}).encode("utf-8")
    tampered_body = json.dumps({"job_id": "evil"}).encode("utf-8")

    response = client.post(
        "/api/v1/scans/process",
        content=tampered_body,
        headers={"Upstash-Signature": _token(signed_body)},
    )

    assert response.status_code == 401
    assert processor.processed == []
