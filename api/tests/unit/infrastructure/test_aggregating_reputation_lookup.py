import pytest

from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)
from app.infrastructure.reputation.aggregating_reputation_lookup import (
    AggregatingReputationLookup,
)
from app.infrastructure.reputation.circuit_breaker_reputation_lookup import (
    CircuitBreakerReputationLookup,
)
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker


def _match(provider: str, confidence: float, references: int = 1) -> ReputationMatch:
    return ReputationMatch(
        queried_value="evil.example",
        provider_name=provider,
        confidence=confidence,
        reference_count=references,
        match_scope="host",
        description=f"{provider} flagged host",
    )


class StubProvider(ReputationLookupPort):
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls = 0

    def lookup(self, hostname: str):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result


def test_no_matches_returns_none() -> None:
    aggregator = AggregatingReputationLookup(
        providers=(StubProvider(None), StubProvider(None)),
        consensus_threshold=2,
    )
    assert aggregator.lookup("evil.example") is None


def test_single_match_is_returned_as_is() -> None:
    urlhaus = _match("urlhaus.abuse.ch", confidence=99.0)
    aggregator = AggregatingReputationLookup(
        providers=(StubProvider(urlhaus), StubProvider(None)),
        consensus_threshold=2,
    )

    result = aggregator.lookup("evil.example")

    assert result == urlhaus  # authoritative single source preserved (terminal)


def test_two_providers_reach_consensus_and_boost() -> None:
    aggregator = AggregatingReputationLookup(
        providers=(
            StubProvider(_match("urlhaus.abuse.ch", confidence=96.0, references=2)),
            StubProvider(_match("openphish.com", confidence=95.0, references=1)),
        ),
        consensus_threshold=2,
        boosted_confidence=99.0,
    )

    result = aggregator.lookup("evil.example")

    assert result is not None
    assert result.confidence >= 99.0  # boosted to terminal grade
    assert result.reference_count == 3  # summed
    assert "openphish.com" in result.provider_name
    assert "urlhaus.abuse.ch" in result.provider_name


def test_single_weaker_match_is_not_boosted() -> None:
    openphish = _match("openphish.com", confidence=95.0)
    aggregator = AggregatingReputationLookup(
        providers=(StubProvider(None), StubProvider(openphish)),
        consensus_threshold=2,
    )

    result = aggregator.lookup("evil.example")

    assert result is not None
    assert result.confidence == 95.0  # stays below terminal threshold


def test_provider_error_is_isolated() -> None:
    good = _match("urlhaus.abuse.ch", confidence=99.0)
    aggregator = AggregatingReputationLookup(
        providers=(
            StubProvider(error=ReputationLookupError("boom")),
            StubProvider(good),
        ),
        consensus_threshold=2,
    )

    result = aggregator.lookup("evil.example")

    assert result == good  # the healthy provider still produces a verdict


def test_all_providers_unavailable_raises() -> None:
    aggregator = AggregatingReputationLookup(
        providers=(
            StubProvider(error=ReputationLookupError("down")),
            StubProvider(error=ConnectionError("down")),
        ),
        consensus_threshold=2,
    )

    with pytest.raises(ReputationLookupError):
        aggregator.lookup("evil.example")


def test_open_circuit_provider_does_not_block_consensus_or_raise() -> None:
    # One provider's breaker is open; the other is healthy and flags the host.
    open_breaker = CircuitBreaker(failure_threshold=1, reset_seconds=999)
    open_breaker.record_failure()  # trips it open
    guarded_open = CircuitBreakerReputationLookup(
        inner=StubProvider(_match("openphish.com", 95.0)),
        breaker=open_breaker,
        provider_name="openphish.com",
    )
    healthy = StubProvider(_match("urlhaus.abuse.ch", 99.0))

    aggregator = AggregatingReputationLookup(
        providers=(guarded_open, healthy), consensus_threshold=2
    )

    result = aggregator.lookup("evil.example")

    assert result is not None
    assert result.provider_name == "urlhaus.abuse.ch"  # single healthy match, as-is
    assert guarded_open.inner.calls == 0  # open circuit short-circuited the call


def test_single_provider_aggregator_preserves_passthrough() -> None:
    match = _match("urlhaus.abuse.ch", 99.0)
    aggregator = AggregatingReputationLookup(
        providers=(StubProvider(match),), consensus_threshold=2
    )

    assert aggregator.lookup("evil.example") == match
    assert aggregator.lookup("evil.example") == match
