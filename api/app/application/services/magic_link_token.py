import hashlib
import secrets


def generate_magic_link_token() -> str:
    """A high-entropy, URL-safe single-use token."""
    return secrets.token_urlsafe(32)


def hash_magic_link_token(token: str) -> str:
    """Deterministic hash stored server-side; the raw token is never persisted."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
