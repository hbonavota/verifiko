from __future__ import annotations

import contextlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class JsonRedisCache:
    """A small read-through JSON cache over Redis.

    Design guarantees:
    - The cache is never allowed to break a request: any Redis error (get or
      set) or corrupt entry degrades transparently to calling the loader.
    - Negative results (``None``) are cached too, so repeated lookups of hosts
      that no provider knows about do not keep hitting the network.
    - Loader exceptions are never cached: a failed upstream call propagates and
      the next request retries.
    """

    redis_client: Any
    key_prefix: str
    ttl_seconds: int

    def get_or_call(
        self,
        key: str,
        loader: Callable[[], T],
        encode: Callable[[T], Any],
        decode: Callable[[Any], T],
    ) -> T:
        full_key = f"{self.key_prefix}:{key}"

        cached = self._safe_get(full_key)
        if cached is not None:
            try:
                return decode(json.loads(cached))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                # Corrupt or schema-drifted entry: ignore and recompute.
                pass

        value = loader()

        try:
            serialized = json.dumps(encode(value))
        except (TypeError, ValueError):
            return value
        self._safe_setex(full_key, serialized)
        return value

    def _safe_get(self, full_key: str) -> str | None:
        try:
            return self.redis_client.get(full_key)
        except Exception:
            return None

    def _safe_setex(self, full_key: str, serialized: str) -> None:
        with contextlib.suppress(Exception):
            self.redis_client.setex(full_key, self.ttl_seconds, serialized)
