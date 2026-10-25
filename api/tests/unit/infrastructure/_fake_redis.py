"""A tiny in-memory Redis fake that emulates the two Lua scripts used by the
rate/quota limiters (evaluated via ``eval``), plus the handful of plain commands
the limiters call (``get``, ``scan_iter``, ``delete``).

The limiters now push their logic into single ``EVAL`` calls, so the fake
interprets those scripts by their shape: the rate-limit script references ``TTL``
and returns an integer retry-after; the quota script does a ``GET`` guard and
returns a ``{used, allowed}`` pair.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FakeRedis:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or (lambda: 0.0)
        self._values: dict[str, int] = {}
        self._expiry: dict[str, float] = {}

    # -- command emulation ------------------------------------------------
    def eval(self, script: str, numkeys: int, *args: Any) -> Any:
        keys = list(args[:numkeys])
        argv = list(args[numkeys:])
        key = keys[0]
        self._purge(key)
        if "TTL" in script:
            return self._rate_limit(key, int(argv[0]), int(argv[1]))
        return self._quota_consume(key, int(argv[0]), int(argv[1]))

    def get(self, key: str) -> str | None:
        self._purge(key)
        value = self._values.get(key)
        return None if value is None else str(value)

    def scan_iter(self, match: str):
        prefix = match[:-1] if match.endswith("*") else match
        for key in tuple(self._values):
            if key.startswith(prefix):
                yield key

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._values:
                removed += 1
                self._values.pop(key, None)
                self._expiry.pop(key, None)
        return removed

    # -- script bodies ----------------------------------------------------
    def _rate_limit(self, key: str, window: int, limit: int) -> int:
        current = self._values.get(key, 0) + 1
        self._values[key] = current
        if current == 1:
            self._expiry[key] = self._clock() + window
        if current > limit:
            ttl = self._ttl(key)
            return ttl if ttl >= 0 else window
        return -1

    def _quota_consume(self, key: str, limit: int, reset: int) -> list[int]:
        current = self._values.get(key, 0)
        if current >= limit:
            return [current, 0]
        current += 1
        self._values[key] = current
        if current == 1:
            self._expiry[key] = self._clock() + reset
        return [current, 1]

    # -- helpers ----------------------------------------------------------
    def _ttl(self, key: str) -> int:
        exp = self._expiry.get(key)
        if exp is None:
            return -1
        return int(round(exp - self._clock()))

    def _purge(self, key: str) -> None:
        exp = self._expiry.get(key)
        if exp is not None and self._clock() >= exp:
            self._values.pop(key, None)
            self._expiry.pop(key, None)
