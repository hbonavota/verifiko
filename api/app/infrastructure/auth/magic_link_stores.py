from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from app.application.ports.magic_link_store import MagicLinkStorePort


class InMemoryMagicLinkStore(MagicLinkStorePort):
    """Process-local single-use token store for dev and single-replica use."""

    def __init__(self, time_source: Callable[[], float] = time.monotonic) -> None:
        self._entries: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._time = time_source

    def save(self, token_hash: str, email: str, ttl_seconds: int) -> None:
        with self._lock:
            self._entries[token_hash] = (email, self._time() + ttl_seconds)

    def consume(self, token_hash: str) -> str | None:
        with self._lock:
            entry = self._entries.pop(token_hash, None)
        if entry is None:
            return None
        email, expires_at = entry
        if self._time() > expires_at:
            return None
        return email


class RedisMagicLinkStore(MagicLinkStorePort):
    """Redis-backed store; ``consume`` uses GETDEL for atomic single use."""

    def __init__(self, redis_client: Any, key_prefix: str) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix

    def save(self, token_hash: str, email: str, ttl_seconds: int) -> None:
        self._redis.setex(self._key(token_hash), ttl_seconds, email)

    def consume(self, token_hash: str) -> str | None:
        return self._redis.getdel(self._key(token_hash))

    def _key(self, token_hash: str) -> str:
        return f"{self._key_prefix}:{token_hash}"
