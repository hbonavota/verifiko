import json

from app.infrastructure.cache.json_redis_cache import JsonRedisCache


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.get_calls = 0

    def get(self, key: str):
        self.get_calls += 1
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl


class ExplodingRedis:
    def get(self, key: str):
        raise ConnectionError("redis down")

    def setex(self, key: str, ttl: int, value: str) -> None:
        raise ConnectionError("redis down")


def _identity_cache(redis) -> JsonRedisCache:
    return JsonRedisCache(redis_client=redis, key_prefix="test", ttl_seconds=42)


def test_miss_calls_loader_and_stores_with_ttl() -> None:
    redis = FakeRedis()
    cache = _identity_cache(redis)
    calls = []

    value = cache.get_or_call(
        key="k",
        loader=lambda: calls.append(1) or {"v": 1},
        encode=lambda v: v,
        decode=lambda p: p,
    )

    assert value == {"v": 1}
    assert len(calls) == 1
    assert redis.store["test:k"] == json.dumps({"v": 1})
    assert redis.ttls["test:k"] == 42


def test_hit_returns_cached_without_calling_loader() -> None:
    redis = FakeRedis()
    redis.store["test:k"] = json.dumps({"v": 7})
    cache = _identity_cache(redis)
    calls = []

    value = cache.get_or_call(
        key="k",
        loader=lambda: calls.append(1) or {"v": 999},
        encode=lambda v: v,
        decode=lambda p: p,
    )

    assert value == {"v": 7}
    assert calls == []


def test_negative_result_is_cached_and_reused() -> None:
    redis = FakeRedis()
    cache = _identity_cache(redis)
    loader_calls = []

    def loader():
        loader_calls.append(1)
        return None

    first = cache.get_or_call("k", loader, encode=lambda v: v, decode=lambda p: p)
    second = cache.get_or_call("k", loader, encode=lambda v: v, decode=lambda p: p)

    assert first is None
    assert second is None
    # The miss stored "null"; the second call is a hit, so loader runs once.
    assert len(loader_calls) == 1
    assert redis.store["test:k"] == "null"


def test_redis_failure_degrades_to_loader() -> None:
    cache = _identity_cache(ExplodingRedis())
    calls = []

    value = cache.get_or_call(
        key="k",
        loader=lambda: calls.append(1) or {"v": 5},
        encode=lambda v: v,
        decode=lambda p: p,
    )

    assert value == {"v": 5}
    assert len(calls) == 1


def test_corrupt_entry_is_ignored_and_recomputed() -> None:
    redis = FakeRedis()
    redis.store["test:k"] = "{not valid json"
    cache = _identity_cache(redis)

    value = cache.get_or_call(
        key="k",
        loader=lambda: {"v": 3},
        encode=lambda v: v,
        decode=lambda p: p,
    )

    assert value == {"v": 3}
    assert redis.store["test:k"] == json.dumps({"v": 3})


def test_loader_exception_is_not_cached() -> None:
    redis = FakeRedis()
    cache = _identity_cache(redis)

    class Boom(Exception):
        pass

    def loader():
        raise Boom()

    try:
        cache.get_or_call("k", loader, encode=lambda v: v, decode=lambda p: p)
    except Boom:
        pass
    else:  # pragma: no cover
        raise AssertionError("loader exception should propagate")

    assert "test:k" not in redis.store
