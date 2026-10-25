from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.application.ports.scan_webhook_notifier import ScanWebhookNotifierPort
from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
)
from app.infrastructure.external_services.pinned_http_client import (
    send_pinned_post_request,
)

logger = logging.getLogger(__name__)

WebhookPoster = Callable[[str, dict[str, str], bytes], int]
"""(url, headers, body) -> HTTP status code."""


@dataclass(slots=True)
class HttpScanWebhookNotifier(ScanWebhookNotifierPort):
    """Delivers a signed, SSRF-guarded webhook when a scan reaches a terminal
    state.

    - The destination is validated with the same outbound guard used for
      verification targets, so a webhook can never be used to reach private or
      special-use addresses (SSRF).
    - The payload is signed with HMAC-SHA256 over ``"{timestamp}." + body`` so
      the receiver can verify authenticity and reject replays.
    - Delivery is best-effort with a bounded retry; a persistent failure is
      logged, never raised (the poll endpoint stays authoritative).
    """

    signing_secret: str
    target_validator: Callable[[str], None]
    http_poster: WebhookPoster
    max_attempts: int = 3
    backoff_seconds: float = 0.5
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(UTC)
    delivery_id_factory: Callable[[], str] = field(default=lambda: uuid.uuid4().hex)
    sleep: Callable[[float], None] = field(default=time.sleep)

    def notify(self, job: VerificationJob) -> None:
        if not job.webhook_url:
            return

        try:
            self.target_validator(job.webhook_url)
        except UnsafeOutboundTargetError:
            logger.warning("Skipping webhook for scan %s: unsafe destination", job.id)
            return

        event = self._event_name(job.status)
        body = json.dumps(self._payload(job, event)).encode("utf-8")
        headers = self._headers(event, body)

        for attempt in range(self.max_attempts):
            try:
                status = self.http_poster(job.webhook_url, headers, body)
                if 200 <= status < 300:
                    return
                logger.warning(
                    "Webhook for scan %s returned HTTP %s (attempt %s)",
                    job.id,
                    status,
                    attempt + 1,
                )
            except Exception as exc:  # noqa: BLE001 - delivery is best-effort
                logger.warning(
                    "Webhook delivery error for scan %s (attempt %s): %s",
                    job.id,
                    attempt + 1,
                    exc,
                )
            if attempt < self.max_attempts - 1:
                self.sleep(self.backoff_seconds * (attempt + 1))

        logger.warning(
            "Webhook for scan %s gave up after %s attempts", job.id, self.max_attempts
        )

    @staticmethod
    def _event_name(status: VerificationJobStatus) -> str:
        return (
            "scan.completed"
            if status is VerificationJobStatus.COMPLETED
            else "scan.failed"
        )

    def _payload(self, job: VerificationJob, event: str) -> dict:
        return {
            "event": event,
            "scan_id": job.id,
            "status": job.status.value.lower(),
            "url": job.url,
            "result_verification_id": job.result_verification_id,
            "error": job.error_message,
            "occurred_at": _iso_utc(self.current_time_provider()),
        }

    def _headers(self, event: str, body: bytes) -> dict[str, str]:
        timestamp = str(int(self.current_time_provider().timestamp()))
        signature = self._sign(timestamp, body)
        return {
            "Content-Type": "application/json",
            "User-Agent": "Verifiko-Webhook/1.0",
            "X-Verifiko-Event": event,
            "X-Verifiko-Delivery": self.delivery_id_factory(),
            "X-Verifiko-Timestamp": timestamp,
            "X-Verifiko-Signature": f"sha256={signature}",
        }

    def _sign(self, timestamp: str, body: bytes) -> str:
        message = f"{timestamp}.".encode() + body
        return hmac.new(
            self.signing_secret.encode("utf-8"), message, hashlib.sha256
        ).hexdigest()


def _iso_utc(value: datetime) -> str:
    normalized = (
        value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    )
    return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_pinned_webhook_poster(timeout_seconds: float = 5.0) -> WebhookPoster:
    """A poster that pins the connection to the guard-validated IP and does not
    follow redirects.

    Using ``urllib.urlopen`` here would re-resolve DNS at connect time (a TOCTOU
    gap: a low-TTL host can pass the guard's pre-check with a public IP and then
    connect to a private one) and would follow 3xx redirects to an attacker-
    chosen ``Location`` (forwarding the signed ``X-Verifiko-*`` headers off to an
    internal host). Delivering through the pinned client closes both: the socket
    connects only to the already-validated address, and ``http.client`` returns a
    redirect as a plain 3xx status instead of following it. Any guard, transport,
    or protocol failure surfaces as ``WebhookDeliveryError`` so the notifier
    retries or gives up without ever contacting an unsafe address.
    """

    def _post(url: str, headers: dict[str, str], body: bytes) -> int:
        try:
            response = send_pinned_post_request(
                url,
                headers=headers,
                body=body,
                timeout_seconds=timeout_seconds,
            )
        except (UnsafeOutboundTargetError, http.client.HTTPException, OSError) as exc:
            raise WebhookDeliveryError(str(exc)) from exc
        return response.status_code

    return _post


class WebhookDeliveryError(Exception):
    """Raised by the default poster on a transport-level failure."""
