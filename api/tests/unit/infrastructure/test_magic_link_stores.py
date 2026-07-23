from app.infrastructure.auth.magic_link_stores import (
    InMemoryMagicLinkStore,
    RedisMagicLinkStore,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl

    def getdel(self, key: str):
        self.ttls.pop(key, None)
        return self.store.pop(key, None)


def test_in_memory_consume_returns_email_once() -> None:
    store = InMemoryMagicLinkStore()
    store.save("hash-1", "user@example.com", 900)

    assert store.consume("hash-1") == "user@example.com"
    assert store.consume("hash-1") is None  # single use


def test_in_memory_expired_token_is_none() -> None:
    clock = FakeClock()
    store = InMemoryMagicLinkStore(time_source=clock)
    store.save("hash-1", "user@example.com", 100)

    clock.advance(101)
    assert store.consume("hash-1") is None


def test_redis_uses_getdel_for_single_use() -> None:
    redis = FakeRedis()
    store = RedisMagicLinkStore(redis, key_prefix="verifiko:magic-link")
    store.save("hash-1", "user@example.com", 900)

    assert redis.ttls["verifiko:magic-link:hash-1"] == 900
    assert store.consume("hash-1") == "user@example.com"
    assert store.consume("hash-1") is None
    assert "verifiko:magic-link:hash-1" not in redis.store
