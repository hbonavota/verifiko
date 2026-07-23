from abc import ABC, abstractmethod


class MagicLinkStorePort(ABC):
    """Single-use storage for magic-link tokens.

    Only a hash of the token is stored, mapped to the target email, with a
    short TTL. ``consume`` must atomically return-and-delete so a link can be
    used at most once.
    """

    @abstractmethod
    def save(self, token_hash: str, email: str, ttl_seconds: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def consume(self, token_hash: str) -> str | None:
        raise NotImplementedError
