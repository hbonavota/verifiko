from datetime import datetime, timezone

from app.application.ports.domain_age_lookup import DomainAgeLookupPort, DomainRegistrationInfo
from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.reputation_lookup import ReputationLookupPort, ReputationMatch
from app.infrastructure.cache.caching_domain_age_lookup import CachingDomainAgeLookup
from app.infrastructure.cache.caching_infrastructure_lookup import CachingInfrastructureLookup
from app.infrastructure.cache.caching_reputation_lookup import CachingReputationLookup
from app.infrastructure.cache.json_redis_cache import JsonRedisCache


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str):
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl


class CountingReputation(ReputationLookupPort):
    def __init__(self, result) -> None:
        self.result = result
        self.calls = 0

    def lookup(self, hostname: str):
        self.calls += 1
        return self.result


class CountingDomainAge(DomainAgeLookupPort):
    def __init__(self, result) -> None:
        self.result = result
        self.calls = 0

    def lookup(self, domain: str):
        self.calls += 1
        return self.result


class CountingInfrastructure(InfrastructureLookupPort):
    def __init__(self, result) -> None:
        self.result = result
        self.calls = 0

    def lookup(self, hostname: str, port: int | None = None):
        self.calls += 1
        return self.result


def _cache(redis) -> JsonRedisCache:
    return JsonRedisCache(redis_client=redis, key_prefix="verifiko:analysis", ttl_seconds=100)


def test_reputation_match_round_trips_and_caches() -> None:
    match = ReputationMatch(
        queried_value="evil.example",
        provider_name="urlhaus.abuse.ch",
        confidence=99.0,
        reference_count=3,
        match_scope="host",
        description="known bad",
    )
    inner = CountingReputation(match)
    redis = FakeRedis()
    adapter = CachingReputationLookup(inner=inner, cache=_cache(redis))

    first = adapter.lookup("Evil.Example")
    second = adapter.lookup("evil.example")

    assert first == match
    assert second == match
    assert inner.calls == 1  # second call served from cache
    assert redis.ttls["verifiko:analysis:reputation:evil.example"] == 100


def test_reputation_negative_is_cached() -> None:
    inner = CountingReputation(None)
    adapter = CachingReputationLookup(inner=inner, cache=_cache(FakeRedis()))

    assert adapter.lookup("clean.example") is None
    assert adapter.lookup("clean.example") is None
    assert inner.calls == 1


def test_domain_age_round_trips_with_datetime() -> None:
    info = DomainRegistrationInfo(
        registered_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        provider_name="rdap",
    )
    inner = CountingDomainAge(info)
    adapter = CachingDomainAgeLookup(inner=inner, cache=_cache(FakeRedis()))

    first = adapter.lookup("example.com")
    second = adapter.lookup("example.com")

    assert first == info
    assert second == info
    assert inner.calls == 1


def test_infrastructure_profile_round_trips_with_addresses() -> None:
    profile = InfrastructureProfile(
        queried_host="example.com",
        provider_name="socket",
        resolved_addresses=(
            ResolvedAddress(ip_address="203.0.113.10", reverse_hostname="host.example"),
            ResolvedAddress(ip_address="203.0.113.11"),
        ),
    )
    inner = CountingInfrastructure(profile)
    adapter = CachingInfrastructureLookup(inner=inner, cache=_cache(FakeRedis()))

    first = adapter.lookup("example.com", 443)
    second = adapter.lookup("example.com", 443)

    assert first == profile
    assert second == profile
    assert inner.calls == 1


def test_infrastructure_cache_key_includes_port() -> None:
    inner = CountingInfrastructure(
        InfrastructureProfile(
            queried_host="example.com", provider_name="socket", resolved_addresses=()
        )
    )
    redis = FakeRedis()
    adapter = CachingInfrastructureLookup(inner=inner, cache=_cache(redis))

    adapter.lookup("example.com", 443)
    adapter.lookup("example.com", 8443)

    assert inner.calls == 2  # different ports are distinct cache entries
    assert "verifiko:analysis:infrastructure:example.com:443" in redis.store
    assert "verifiko:analysis:infrastructure:example.com:8443" in redis.store
