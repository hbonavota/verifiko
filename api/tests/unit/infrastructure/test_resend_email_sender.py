import json

import pytest

from app.application.ports.email_sender import EmailDeliveryError, EmailMessage
from app.infrastructure.email.resend_email_sender import ResendEmailSender


class RecordingPoster:
    def __init__(self, status: int) -> None:
        self.status = status
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return self.status


def _message() -> EmailMessage:
    return EmailMessage(to="user@example.com", subject="Hi", html="<p>Hi</p>", text="Hi")


def test_sends_expected_payload_and_auth_header() -> None:
    poster = RecordingPoster(200)
    ResendEmailSender(
        api_key="re_test_key", from_email="login@verifiko.es", http_poster=poster
    ).send(_message())

    assert len(poster.calls) == 1
    call = poster.calls[0]
    assert call["headers"]["Authorization"] == "Bearer re_test_key"
    payload = json.loads(call["body"])
    assert payload["from"] == "login@verifiko.es"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "Hi"
    assert payload["html"] == "<p>Hi</p>"


def test_non_2xx_raises_delivery_error() -> None:
    poster = RecordingPoster(422)
    sender = ResendEmailSender(
        api_key="re_test_key", from_email="login@verifiko.es", http_poster=poster
    )
    with pytest.raises(EmailDeliveryError):
        sender.send(_message())
