from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.infrastructure.cache.json_redis_cache import JsonRedisCache


@dataclass(slots=True)
class CachingInfrastructureLookup(InfrastructureLookupPort):
    """Read-through Redis cache in front of an infrastructure (DNS) provider.

    Keyed by hostname and port. Provider errors are not cached and propagate to
    the caller.
    """

    inner: InfrastructureLookupPort
    cache: JsonRedisCache

    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        return self.cache.get_or_call(
            key=f"infrastructure:{hostname.lower()}:{port}",
            loader=lambda: self.inner.lookup(hostname, port),
            encode=_encode,
            decode=_decode,
        )


def _encode(profile: InfrastructureProfile) -> dict:
    return {
        "queried_host": profile.queried_host,
        "provider_name": profile.provider_name,
        "resolved_addresses": [
            {"ip_address": address.ip_address, "reverse_hostname": address.reverse_hostname}
            for address in profile.resolved_addresses
        ],
    }


def _decode(payload: dict) -> InfrastructureProfile:
    return InfrastructureProfile(
        queried_host=payload["queried_host"],
        provider_name=payload["provider_name"],
        resolved_addresses=tuple(
            ResolvedAddress(
                ip_address=address["ip_address"],
                reverse_hostname=address.get("reverse_hostname"),
            )
            for address in payload["resolved_addresses"]
        ),
    )
