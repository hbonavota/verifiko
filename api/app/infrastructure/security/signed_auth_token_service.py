import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from app.application.ports.auth_token_service import AuthTokenError, AuthTokenServicePort
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class SignedAuthTokenService(AuthTokenServicePort):
    secret: str
    ttl_seconds: int

    def issue_access_token(self, user_id: UserId) -> str:
        if not self.secret:
            raise AuthTokenError("Authentication token secret is not configured.")

        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + self.ttl_seconds,
            "typ": "verifiko-auth",
        }
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        encoded_payload = self._b64encode(payload_bytes)
        signature = self._sign(encoded_payload.encode("ascii"))
        return f"{encoded_payload}.{self._b64encode(signature)}"

    def resolve_user_id(self, token: str) -> UserId:
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
        except ValueError as exc:
            raise AuthTokenError("Authentication token is malformed.") from exc

        expected_signature = self._sign(encoded_payload.encode("ascii"))
        provided_signature = self._b64decode(encoded_signature)
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise AuthTokenError("Authentication token signature is invalid.")

        try:
            payload = json.loads(self._b64decode(encoded_payload))
        except (json.JSONDecodeError, ValueError) as exc:
            raise AuthTokenError("Authentication token payload is invalid.") from exc

        if payload.get("typ") != "verifiko-auth":
            raise AuthTokenError("Authentication token type is invalid.")
        exp = payload.get("exp")
        sub = payload.get("sub")
        if not isinstance(exp, int) or not isinstance(sub, str):
            raise AuthTokenError("Authentication token payload is incomplete.")
        if exp < int(time.time()):
            raise AuthTokenError("Authentication token has expired.")
        return UserId.from_string(sub)

    def _sign(self, payload: bytes) -> bytes:
        return hmac.new(self.secret.encode("utf-8"), payload, hashlib.sha256).digest()

    @staticmethod
    def _b64encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
