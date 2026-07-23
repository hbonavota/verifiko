from __future__ import annotations

import threading
import time
from typing import Callable


class CircuitOpenError(Exception):
    """Raised when a call is short-circuited because the breaker is open."""


class CircuitBreaker:
    """A minimal thread-safe circuit breaker.

    After ``failure_threshold`` consecutive failures the breaker opens and
    short-circuits calls for ``reset_seconds``. It then allows a trial call
    (half-open); a success closes it, another failure re-opens it. This protects
    a slow or failing dependency from being hammered and from dragging request
    latency through repeated timeouts.
    """

    _CLOSED = "closed"
    _OPEN = "open"
    _HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_seconds: float = 30.0,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._time_source = time_source
        self._lock = threading.Lock()
        self._state = self._CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def allow(self) -> bool:
        """Whether a call may proceed right now."""
        with self._lock:
            if self._state == self._OPEN:
                assert self._opened_at is not None
                if self._time_source() - self._opened_at >= self._reset_seconds:
                    self._state = self._HALF_OPEN
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = self._CLOSED
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._state == self._HALF_OPEN or self._failure_count >= self._failure_threshold:
                self._state = self._OPEN
                self._opened_at = self._time_source()
