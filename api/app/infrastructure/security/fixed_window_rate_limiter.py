import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic


@dataclass(slots=True)
class FixedWindowRateLimiter:
    max_requests: int
    window_seconds: int
    now_provider: Callable[[], float] = monotonic
    _requests_by_key: dict[str, deque[float]] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def check(self, key: str) -> int | None:
        now = self.now_provider()
        window_start = now - self.window_seconds

        with self._lock:
            requests = self._requests_by_key.setdefault(key, deque())
            while requests and requests[0] <= window_start:
                requests.popleft()

            if len(requests) >= self.max_requests:
                retry_after = requests[0] + self.window_seconds - now
                return max(1, math.ceil(retry_after))

            requests.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._requests_by_key.clear()
