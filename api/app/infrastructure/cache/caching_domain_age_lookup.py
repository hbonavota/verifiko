from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
)
from app.infrastructure.cache.json_redis_cache import JsonRedisCache


@dataclass(slots=True)
class CachingDomainAgeLookup(DomainAgeLookupPort):
    """Read-through Redis cache in front of a domain-age provider.

    Registration dates change slowly, so this layer tolerates a long TTL.
    Provider errors are not cached and propagate to the caller.
    """

    inner: DomainAgeLookupPort
    cache: JsonRedisCache

    def lookup(self, domain: str) -> DomainRegistrationInfo | None:
        return self.cache.get_or_call(
            key=f"domain-age:{domain.lower()}",
            loader=lambda: self.inner.lookup(domain),
            encode=_encode,
            decode=_decode,
        )


def _encode(info: DomainRegistrationInfo | None) -> dict | None:
    if info is None:
        return None
    return {
        "registered_at": info.registered_at.isoformat(),
        "provider_name": info.provider_name,
    }


def _decode(payload: dict | None) -> DomainRegistrationInfo | None:
    if payload is None:
        return None
    return DomainRegistrationInfo(
        registered_at=datetime.fromisoformat(payload["registered_at"]),
        provider_name=payload["provider_name"],
    )
