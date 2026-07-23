import hashlib
import secrets
from dataclasses import dataclass

from app.application.ports.api_key_token_service import (
    ApiKeyTokenServicePort,
    GeneratedApiKey,
)

API_KEY_PREFIX = "vfk_"
API_KEY_LIVE_PREFIX = "vfk_live_"
_SECRET_BYTES = 32
_DISPLAY_PREFIX_LENGTH = 16


@dataclass(slots=True)
class Sha256ApiKeyTokenService(ApiKeyTokenServicePort):
    """Generates high-entropy API keys and derives a deterministic lookup hash.

    API keys are random secrets (not user-chosen passwords), so a fast
    unsalted SHA-256 is the correct choice for the lookup hash: it lets the
    repository find a key by an indexed equality match while never storing the
    secret itself.
    """

    live_prefix: str = API_KEY_LIVE_PREFIX

    def generate(self) -> GeneratedApiKey:
        plaintext = f"{self.live_prefix}{secrets.token_urlsafe(_SECRET_BYTES)}"
        return GeneratedApiKey(
            plaintext=plaintext,
            token_prefix=plaintext[:_DISPLAY_PREFIX_LENGTH],
            token_hash=self.hash(plaintext),
        )

    def hash(self, plaintext: str) -> str:
        return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

    def looks_like_api_key(self, candidate: str) -> bool:
        return candidate.startswith(API_KEY_PREFIX)
