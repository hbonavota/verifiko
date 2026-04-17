from app.infrastructure.security.redis_fixed_window_rate_limiter import RedisFixedWindowRateLimiter


class FakeRedisPipeline:
    def __init__(self, client: "FakeRedisClient") -> None:
        self._client = client
        self._commands: list[tuple[str, str, object]] = []

    def __enter__(self) -> "FakeRedisPipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._commands.clear()

    def watch(self, key: str) -> None:
        return None

    def zremrangebyscore(self, key: str, minimum, maximum) -> int:
        return self._client.zremrangebyscore(key, minimum, maximum)

    def zcard(self, key: str) -> int:
        return self._client.zcard(key)

    def zrange(self, key: str, start: int, stop: int, *, withscores: bool = False):
        return self._client.zrange(key, start, stop, withscores=withscores)

    def multi(self) -> None:
        return None

    def zadd(self, key: str, mapping: dict[str, float]) -> None:
        self._commands.append(("zadd", key, mapping))

    def expire(self, key: str, ttl: int) -> None:
        self._commands.append(("expire", key, ttl))

    def execute(self) -> list[int | bool]:
        results: list[int | bool] = []
        for command, key, value in self._commands:
            if command == "zadd":
                results.append(self._client.zadd(key, value))
            elif command == "expire":
                results.append(self._client.expire(key, value))
        self._commands.clear()
        return results

    def unwatch(self) -> None:
        return None


class FakeRedisClient:
    def __init__(self) -> None:
        self._sorted_sets: dict[str, dict[str, float]] = {}

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self)

    def zremrangebyscore(self, key: str, minimum, maximum) -> int:
        members = self._sorted_sets.get(key, {})
        max_score = float(maximum)
        to_remove = [member for member, score in members.items() if score <= max_score]
        for member in to_remove:
            members.pop(member, None)
        if not members:
            self._sorted_sets.pop(key, None)
        return len(to_remove)

    def zcard(self, key: str) -> int:
        return len(self._sorted_sets.get(key, {}))

    def zrange(self, key: str, start: int, stop: int, *, withscores: bool = False):
        members = sorted(self._sorted_sets.get(key, {}).items(), key=lambda item: item[1])
        if stop == -1:
            selection = members[start:]
        else:
            selection = members[start : stop + 1]
        if withscores:
            return selection
        return [member for member, _ in selection]

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        members = self._sorted_sets.setdefault(key, {})
        added = 0
        for member, score in mapping.items():
            if member not in members:
                added += 1
            members[member] = score
        return added

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def scan_iter(self, match: str):
        prefix = match[:-1] if match.endswith("*") else match
        for key in tuple(self._sorted_sets):
            if key.startswith(prefix):
                yield key

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._sorted_sets:
                removed += 1
                self._sorted_sets.pop(key, None)
        return removed


def test_redis_fixed_window_rate_limiter_blocks_after_limit_and_returns_retry_after() -> None:
    current_time = 100.0
    limiter = RedisFixedWindowRateLimiter(
        redis_client=FakeRedisClient(),
        max_requests=2,
        window_seconds=10,
        now_provider=lambda: current_time,
    )

    assert limiter.check("203.0.113.10") is None
    current_time = 101.0
    assert limiter.check("203.0.113.10") is None
    current_time = 102.0
    assert limiter.check("203.0.113.10") == 8


def test_redis_fixed_window_rate_limiter_allows_after_window_expires() -> None:
    current_time = 100.0
    limiter = RedisFixedWindowRateLimiter(
        redis_client=FakeRedisClient(),
        max_requests=1,
        window_seconds=10,
        now_provider=lambda: current_time,
    )

    assert limiter.check("203.0.113.10") is None
    current_time = 111.0
    assert limiter.check("203.0.113.10") is None
