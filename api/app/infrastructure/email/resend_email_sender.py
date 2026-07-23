from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.application.ports.email_sender import EmailDeliveryError, EmailMessage, EmailSenderPort

EmailPoster = Callable[[str, dict[str, str], bytes], tuple[int, str]]
"""(url, headers, body) -> (HTTP status code, response body)."""

DEFAULT_RESEND_ENDPOINT = "https://api.resend.com/emails"


@dataclass(slots=True)
class ResendEmailSender(EmailSenderPort):
    """Transactional email via the Resend API."""

    api_key: str
    from_email: str
    http_poster: EmailPoster
    endpoint: str = DEFAULT_RESEND_ENDPOINT

    def send(self, message: EmailMessage) -> None:
        payload = json.dumps(
            {
                "from": self.from_email,
                "to": [message.to],
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
            }
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        status, detail = self.http_poster(self.endpoint, headers, payload)
        if not 200 <= status < 300:
            message = f"Resend returned HTTP {status}"
            if detail:
                message = f"{message}: {detail}"
            raise EmailDeliveryError(message)


def build_urllib_email_poster(timeout_seconds: float = 10.0) -> EmailPoster:
    def _post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.status, ""
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:  # noqa: BLE001 - body may be unavailable
                detail = ""
            return exc.code, detail
        except (URLError, TimeoutError, OSError) as exc:
            raise EmailDeliveryError(str(exc)) from exc

    return _post
