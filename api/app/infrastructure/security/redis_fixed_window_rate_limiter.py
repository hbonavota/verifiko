from dataclasses import dataclass
import logging
from time import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Atomic fixed-window counter evaluated server-side in a single Redis command.
# Returns the seconds until the window resets when the caller is over the limit,
# or -1 when the request is allowed. This replaces the previous sliding-window
# ZSET implementation, which spent ~6 commands (WATCH/ZREMRANGEBYSCORE/ZCARD/
# MULTI/ZADD/EXPIRE) and could retry its optimistic-lock loop. One EVAL keeps the
# hot verification path down to a single Redis command.
_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
if current > tonumber(ARGV[2]) then
  local ttl = redis.call('TTL', KEYS[1])
  if ttl < 0 then
    ttl = tonumber(ARGV[1])
  end
  return ttl
end
return -1
"""


@dataclass(slots=True)
class RedisFixedWindowRateLimiter:
    redis_client: Any
    max_requests: int
    window_seconds: int
    now_provider: Callable[[], float] = time
    key_prefix: str = "verifiko:rate-limit:verifications"

    def check(self, key: str) -> int | None:
        # Fail open: if Redis is unavailable (down, or over its command quota),
        # allow the request rather than turning a rate-limiter outage into an
        # API-wide 5xx. Availability beats strict limiting here.
        try:
            return self._check(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rate limiter unavailable; failing open: %s", exc)
            return None

    def _check(self, key: str) -> int | None:
        redis_key = f"{self.key_prefix}:{key}"
        result = self.redis_client.eval(
            _RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            self.window_seconds,
            self.max_requests,
        )
        retry_after = int(result)
        if retry_after < 0:
            return None
        return max(1, retry_after)

    def reset(self) -> None:
        keys = list(self.redis_client.scan_iter(match=f"{self.key_prefix}:*"))
        if keys:
            self.redis_client.delete(*keys)
