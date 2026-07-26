import base64
import hashlib
import hmac
import json
import time

import pytest

from app.infrastructure.security.qstash_signature_verifier import (
    QStashSignatureError,
    QStashSignatureVerifier,
)


def _seg(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_token(
    signing_key: str,
    body: bytes,
    *,
    exp: int | None = None,
    nbf: int | None = None,
    sub: str | None = None,
    body_claim: str | None = None,
) -> str:
    now = int(time.time())
    payload: dict = {
        "iss": "Upstash",
        "exp": exp if exp is not None else now + 300,
        "nbf": nbf if nbf is not None else now - 10,
        "body": body_claim
        if body_claim is not None
        else base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode("ascii"),
    }
    if sub is not None:
        payload["sub"] = sub
    signing_input = f"{_seg({'alg': 'HS256', 'typ': 'JWT'})}.{_seg(payload)}"
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(signing_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        )
        .rstrip(b"=")
        .decode("ascii")
    )
    return f"{signing_input}.{signature}"


_KEY = "sig-current-key"
_NEXT = "sig-next-key"


def test_valid_signature_passes() -> None:
    body = b'{"job_id": "abc123"}'
    verifier = QStashSignatureVerifier(_KEY, _NEXT)
    verifier.verify(signature=_make_token(_KEY, body), body=body)


def test_standard_base64_body_claim_also_accepted() -> None:
    # QStash client versions have used both the standard and url-safe base64
    # alphabets for the body hash; either must verify.
    body = b'{"job_id": "abc123"}'
    standard_claim = base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
    verifier = QStashSignatureVerifier(_KEY)
    verifier.verify(signature=_make_token(_KEY, body, body_claim=standard_claim), body=body)


def test_signature_from_next_key_passes() -> None:
    body = b'{"job_id": "rotated"}'
    verifier = QStashSignatureVerifier(_KEY, _NEXT)
    verifier.verify(signature=_make_token(_NEXT, body), body=body)


def test_wrong_key_is_rejected() -> None:
    body = b'{"job_id": "abc123"}'
    verifier = QStashSignatureVerifier(_KEY, _NEXT)
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature=_make_token("attacker-key", body), body=body)


def test_tampered_body_is_rejected() -> None:
    signed_body = b'{"job_id": "abc123"}'
    tampered_body = b'{"job_id": "evil"}'
    verifier = QStashSignatureVerifier(_KEY)
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature=_make_token(_KEY, signed_body), body=tampered_body)


def test_expired_signature_is_rejected() -> None:
    body = b'{"job_id": "abc123"}'
    verifier = QStashSignatureVerifier(_KEY, leeway_seconds=0)
    token = _make_token(_KEY, body, exp=int(time.time()) - 120)
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature=token, body=body)


def test_not_yet_valid_signature_is_rejected() -> None:
    body = b'{"job_id": "abc123"}'
    verifier = QStashSignatureVerifier(_KEY, leeway_seconds=0)
    token = _make_token(_KEY, body, nbf=int(time.time()) + 120)
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature=token, body=body)


def test_subject_mismatch_is_rejected_when_url_checked() -> None:
    body = b'{"job_id": "abc123"}'
    verifier = QStashSignatureVerifier(_KEY)
    token = _make_token(_KEY, body, sub="https://evil.example/scans/process")
    with pytest.raises(QStashSignatureError):
        verifier.verify(
            signature=token,
            body=body,
            url="https://api.verifiko.es/api/v1/scans/process",
        )


def test_malformed_token_is_rejected() -> None:
    verifier = QStashSignatureVerifier(_KEY)
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature="not-a-jwt", body=b"{}")


def test_missing_signature_is_rejected() -> None:
    verifier = QStashSignatureVerifier(_KEY)
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature="", body=b"{}")


def test_no_keys_configured_rejects() -> None:
    verifier = QStashSignatureVerifier("", "")
    with pytest.raises(QStashSignatureError):
        verifier.verify(signature=_make_token(_KEY, b"{}"), body=b"{}")
