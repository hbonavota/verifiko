from __future__ import annotations

from dataclasses import asdict, dataclass

from app.application.ports.reputation_lookup import ReputationLookupPort, ReputationMatch
from app.infrastructure.cache.json_redis_cache import JsonRedisCache


@dataclass(slots=True)
class CachingReputationLookup(ReputationLookupPort):
    """Read-through Redis cache in front of a reputation provider.

    Keyed by hostname; both matches and misses are cached. Provider errors are
    not cached and propagate to the caller.
    """

    inner: ReputationLookupPort
    cache: JsonRedisCache

    def lookup(self, hostname: str) -> ReputationMatch | None:
        return self.cache.get_or_call(
            key=f"reputation:{hostname.lower()}",
            loader=lambda: self.inner.lookup(hostname),
            encode=_encode,
            decode=_decode,
        )


def _encode(match: ReputationMatch | None) -> dict | None:
    return None if match is None else asdict(match)


def _decode(payload: dict | None) -> ReputationMatch | None:
    return None if payload is None else ReputationMatch(**payload)
