from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


class QStashSignatureError(Exception):
    """Raised when an ``Upstash-Signature`` header cannot be trusted."""


def _b64url_decode(segment: str) -> bytes:
    """Decode a base64url segment, tolerating missing padding."""
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _b64_any_decode(value: str) -> bytes:
    """Decode base64 that may be standard or url-safe, padded or not.

    QStash encodes the body hash as base64; different client versions have used
    the standard and the url-safe alphabet. We only care about the underlying
    digest bytes, so try both alphabets and compare those.
    """
    normalized = value.strip()
    padding = "=" * (-len(normalized) % 4)
    try:
        return base64.urlsafe_b64decode(normalized + padding)
    except Exception:  # noqa: BLE001
        return base64.b64decode(normalized + padding)


class QStashSignatureVerifier:
    """Verifies the ``Upstash-Signature`` JWT that QStash attaches to every
    message it delivers.

    The header is a JWT (HS256) whose signature is an HMAC over
    ``base64url(header).base64url(payload)`` keyed by the QStash signing key, and
    whose ``body`` claim is the base64 SHA-256 of the forwarded request body.
    Verifying both proves the request really came from QStash and that the body
    was not tampered with in flight. Two keys are accepted so a signing-key
    rotation (current -> next) does not drop in-flight messages.

    This is intentionally dependency-free: the scheme is small and self-contained,
    and avoiding a new runtime dependency keeps the serverless cold start lean.
    """

    def __init__(
        self,
        current_signing_key: str,
        next_signing_key: str = "",
        *,
        leeway_seconds: int = 60,
    ) -> None:
        self._keys = tuple(key for key in (current_signing_key, next_signing_key) if key)
        self._leeway_seconds = leeway_seconds

    def verify(
        self,
        *,
        signature: str,
        body: bytes,
        url: str | None = None,
        now: int | None = None,
    ) -> None:
        """Raise :class:`QStashSignatureError` unless ``signature`` is a valid
        QStash token for ``body`` (and ``url`` when provided)."""
        if not self._keys:
            raise QStashSignatureError("No QStash signing keys are configured.")
        if not signature:
            raise QStashSignatureError("Missing Upstash-Signature header.")

        parts = signature.split(".")
        if len(parts) != 3:
            raise QStashSignatureError("Malformed Upstash-Signature token.")
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

        try:
            provided_signature = _b64url_decode(signature_b64)
        except Exception as exc:  # noqa: BLE001
            raise QStashSignatureError("Unreadable signature segment.") from exc

        if not self._signature_matches_any_key(signing_input, provided_signature):
            raise QStashSignatureError("Signature does not match any signing key.")

        try:
            claims = json.loads(_b64url_decode(payload_b64))
        except Exception as exc:  # noqa: BLE001
            raise QStashSignatureError("Unreadable token payload.") from exc

        self._assert_time_window(claims, now=now)
        self._assert_body_matches(claims, body)
        if url is not None:
            self._assert_subject_matches(claims, url)

    def _signature_matches_any_key(
        self, signing_input: bytes, provided_signature: bytes
    ) -> bool:
        for key in self._keys:
            expected = hmac.new(
                key.encode("utf-8"), signing_input, hashlib.sha256
            ).digest()
            if hmac.compare_digest(expected, provided_signature):
                return True
        return False

    def _assert_time_window(self, claims: dict, *, now: int | None) -> None:
        current_time = now if now is not None else int(time.time())
        exp = claims.get("exp")
        if exp is not None and current_time > int(exp) + self._leeway_seconds:
            raise QStashSignatureError("Signature has expired.")
        nbf = claims.get("nbf")
        if nbf is not None and current_time + self._leeway_seconds < int(nbf):
            raise QStashSignatureError("Signature is not valid yet.")

    def _assert_body_matches(self, claims: dict, body: bytes) -> None:
        claim = claims.get("body")
        if not claim:
            return
        try:
            claim_digest = _b64_any_decode(claim)
        except Exception as exc:  # noqa: BLE001
            raise QStashSignatureError("Unreadable body claim.") from exc
        if not hmac.compare_digest(claim_digest, hashlib.sha256(body).digest()):
            raise QStashSignatureError("Body does not match the signed hash.")

    def _assert_subject_matches(self, claims: dict, url: str) -> None:
        subject = claims.get("sub")
        # QStash sets ``sub`` to the destination URL. Compare only when present so
        # a future token layout that omits it does not break verification.
        if subject and subject != url:
            raise QStashSignatureError("Signature subject does not match the URL.")
