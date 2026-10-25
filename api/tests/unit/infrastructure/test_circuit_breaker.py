from app.infrastructure.resilience.circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_closed_and_allows() -> None:
    breaker = CircuitBreaker(
        failure_threshold=2, reset_seconds=10, time_source=FakeClock()
    )
    assert breaker.state == "closed"
    assert breaker.allow() is True


def test_opens_after_threshold_failures() -> None:
    breaker = CircuitBreaker(
        failure_threshold=2, reset_seconds=10, time_source=FakeClock()
    )

    breaker.record_failure()
    assert breaker.state == "closed"
    breaker.record_failure()

    assert breaker.state == "open"
    assert breaker.allow() is False


def test_success_resets_failure_count() -> None:
    breaker = CircuitBreaker(
        failure_threshold=2, reset_seconds=10, time_source=FakeClock()
    )

    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()

    assert breaker.state == "closed"
    assert breaker.allow() is True


def test_half_opens_after_reset_and_closes_on_success() -> None:
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=10, time_source=clock)

    breaker.record_failure()
    assert breaker.allow() is False

    clock.advance(10)
    assert breaker.allow() is True  # half-open trial
    assert breaker.state == "half_open"

    breaker.record_success()
    assert breaker.state == "closed"


def test_half_open_failure_reopens() -> None:
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=10, time_source=clock)

    breaker.record_failure()
    clock.advance(10)
    breaker.allow()  # -> half_open
    breaker.record_failure()

    assert breaker.state == "open"
    assert breaker.allow() is False
