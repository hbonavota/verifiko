import hashlib
import hmac
import json
from datetime import datetime, timezone

from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.infrastructure.external_services.outbound_target_guard import UnsafeOutboundTargetError
from app.infrastructure.webhooks.http_scan_webhook_notifier import HttpScanWebhookNotifier

_SECRET = "test-webhook-secret"
_NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


class RecordingPoster:
    def __init__(self, statuses) -> None:
        self._statuses = list(statuses)
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return self._statuses[min(len(self.calls) - 1, len(self._statuses) - 1)]


def _job(status=VerificationJobStatus.COMPLETED, webhook_url="https://hooks.example/verifiko"):
    return VerificationJob(
        id="scan-1",
        owner_user_id="owner-1",
        url="https://target.example",
        status=status,
        created_at=_NOW,
        updated_at=_NOW,
        result_verification_id="ver-1" if status is VerificationJobStatus.COMPLETED else None,
        error_message=None if status is VerificationJobStatus.COMPLETED else "boom",
        webhook_url=webhook_url,
    )


def _notifier(poster, *, target_validator=lambda _url: None, max_attempts=3):
    return HttpScanWebhookNotifier(
        signing_secret=_SECRET,
        target_validator=target_validator,
        http_poster=poster,
        max_attempts=max_attempts,
        current_time_provider=lambda: _NOW,
        delivery_id_factory=lambda: "delivery-1",
        sleep=lambda _seconds: None,
    )


def test_delivers_signed_completed_payload() -> None:
    poster = RecordingPoster([200])
    _notifier(poster).notify(_job())

    assert len(poster.calls) == 1
    call = poster.calls[0]
    assert call["url"] == "https://hooks.example/verifiko"
    assert call["headers"]["X-Verifiko-Event"] == "scan.completed"

    payload = json.loads(call["body"])
    assert payload["event"] == "scan.completed"
    assert payload["scan_id"] == "scan-1"
    assert payload["status"] == "completed"
    assert payload["result_verification_id"] == "ver-1"

    # Signature matches HMAC-SHA256 over "{timestamp}." + body.
    timestamp = call["headers"]["X-Verifiko-Timestamp"]
    expected = hmac.new(
        _SECRET.encode(), f"{timestamp}.".encode() + call["body"], hashlib.sha256
    ).hexdigest()
    assert call["headers"]["X-Verifiko-Signature"] == f"sha256={expected}"


def test_failed_job_uses_failed_event() -> None:
    poster = RecordingPoster([200])
    _notifier(poster).notify(_job(status=VerificationJobStatus.FAILED))

    assert poster.calls[0]["headers"]["X-Verifiko-Event"] == "scan.failed"
    payload = json.loads(poster.calls[0]["body"])
    assert payload["status"] == "failed"
    assert payload["error"] == "boom"


def test_unsafe_destination_is_not_delivered() -> None:
    poster = RecordingPoster([200])

    def blocking(_url):
        raise UnsafeOutboundTargetError("blocked")

    _notifier(poster, target_validator=blocking).notify(_job())

    assert poster.calls == []  # SSRF guard prevented delivery


def test_missing_webhook_url_is_a_no_op() -> None:
    poster = RecordingPoster([200])
    _notifier(poster).notify(_job(webhook_url=None))
    assert poster.calls == []


def test_retries_until_success() -> None:
    poster = RecordingPoster([500, 500, 200])
    _notifier(poster).notify(_job())
    assert len(poster.calls) == 3  # two failures then success


def test_gives_up_after_max_attempts_without_raising() -> None:
    poster = RecordingPoster([500])
    _notifier(poster, max_attempts=3).notify(_job())  # must not raise
    assert len(poster.calls) == 3
