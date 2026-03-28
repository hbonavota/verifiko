from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.application.ports.google_identity_verifier import (
    GoogleIdentity,
    GoogleIdentityVerificationError,
    GoogleIdentityVerificationUnavailableError,
    GoogleIdentityVerifierPort,
)


@dataclass(slots=True)
class GoogleTokeninfoIdentityVerifier(GoogleIdentityVerifierPort):
    client_id: str
    timeout_seconds: float = 5.0

    def verify(self, id_token: str) -> GoogleIdentity:
        if not self.client_id:
            raise GoogleIdentityVerificationUnavailableError(
                "Google authentication is not configured for this environment."
            )

        try:
            payload = self._fetch_tokeninfo(id_token)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise GoogleIdentityVerificationError("Google identity token could not be verified.") from exc

        issuer = payload.get("iss")
        audience = payload.get("aud")
        subject = payload.get("sub")
        email = payload.get("email")
        email_verified = payload.get("email_verified")

        if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
            raise GoogleIdentityVerificationError("Google identity token could not be verified.")
        if audience != self.client_id:
            raise GoogleIdentityVerificationError("Google identity token could not be verified.")
        if not isinstance(subject, str) or not subject:
            raise GoogleIdentityVerificationError("Google identity token could not be verified.")
        if not isinstance(email, str) or not email:
            raise GoogleIdentityVerificationError("Google identity token could not be verified.")
        if str(email_verified).lower() != "true":
            raise GoogleIdentityVerificationError("Google identity token could not be verified.")

        display_name = payload.get("name")
        if not isinstance(display_name, str) or not display_name.strip():
            display_name = email

        avatar_url = payload.get("picture")
        if not isinstance(avatar_url, str) or not avatar_url.strip():
            avatar_url = None

        return GoogleIdentity(
            subject=subject,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )

    def _fetch_tokeninfo(self, id_token: str) -> dict[str, object]:
        query = urlencode({"id_token": id_token})
        with urlopen(
            f"https://oauth2.googleapis.com/tokeninfo?{query}",
            timeout=self.timeout_seconds,
        ) as response:
            return json.loads(response.read().decode("utf-8"))
