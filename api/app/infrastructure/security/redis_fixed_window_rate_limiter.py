from dataclasses import dataclass
import math
from time import time
from typing import Any, Callable
from uuid import uuid4


@dataclass(slots=True)
class RedisFixedWindowRateLimiter:
    redis_client: Any
    max_requests: int
    window_seconds: int
    now_provider: Callable[[], float] = time
    key_prefix: str = "verifiko:rate-limit:verifications"

    def check(self, key: str) -> int | None:
        now = self.now_provider()
        window_start = now - self.window_seconds
        redis_key = f"{self.key_prefix}:{key}"
        watch_error = _redis_watch_error_type()

        while True:
            with self.redis_client.pipeline() as pipe:
                try:
                    pipe.watch(redis_key)
                    pipe.zremrangebyscore(redis_key, "-inf", window_start)
                    current = int(pipe.zcard(redis_key))
                    if current >= self.max_requests:
                        oldest = pipe.zrange(redis_key, 0, 0, withscores=True)
                        pipe.unwatch()
                        if not oldest:
                            return 1
                        retry_after = oldest[0][1] + self.window_seconds - now
                        return max(1, math.ceil(retry_after))

                    pipe.multi()
                    pipe.zadd(redis_key, {f"{now}:{uuid4().hex}": now})
                    pipe.expire(redis_key, self.window_seconds)
                    pipe.execute()
                    return None
                except watch_error:
                    continue

    def reset(self) -> None:
        keys = list(self.redis_client.scan_iter(match=f"{self.key_prefix}:*"))
        if keys:
            self.redis_client.delete(*keys)


def _redis_watch_error_type() -> type[Exception]:
    try:
        from redis.exceptions import WatchError
    except Exception:  # pragma: no cover - redis is optional in the local test env
        return RuntimeError
    return WatchError
