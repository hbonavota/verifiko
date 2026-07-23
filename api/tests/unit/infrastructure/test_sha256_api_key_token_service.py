import hashlib

from app.infrastructure.security.sha256_api_key_token_service import (
    API_KEY_LIVE_PREFIX,
    Sha256ApiKeyTokenService,
)


def test_generate_produces_live_prefixed_secret_with_matching_hash() -> None:
    service = Sha256ApiKeyTokenService()

    generated = service.generate()

    assert generated.plaintext.startswith(API_KEY_LIVE_PREFIX)
    assert generated.token_prefix == generated.plaintext[:16]
    assert generated.token_hash == hashlib.sha256(
        generated.plaintext.encode("utf-8")
    ).hexdigest()


def test_generate_is_unique_per_call() -> None:
    service = Sha256ApiKeyTokenService()

    first = service.generate()
    second = service.generate()

    assert first.plaintext != second.plaintext
    assert first.token_hash != second.token_hash


def test_hash_is_deterministic_for_lookup() -> None:
    service = Sha256ApiKeyTokenService()
    generated = service.generate()

    assert service.hash(generated.plaintext) == generated.token_hash


def test_looks_like_api_key_only_matches_prefixed_values() -> None:
    service = Sha256ApiKeyTokenService()

    assert service.looks_like_api_key("vfk_live_abc") is True
    assert service.looks_like_api_key("vfk_something") is True
    assert service.looks_like_api_key("eyJhbGciOi.session.token") is False
    assert service.looks_like_api_key("") is False
