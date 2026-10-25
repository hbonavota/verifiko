import pytest

from app.application.ports.reputation_lookup import ReputationLookupError
from app.infrastructure.reputation.openphish_reputation_client import (
    OpenPhishReputationClient,
    _extract_hosts,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


_FEED = """
# comment line
https://phish.evil.example/login
http://another-phish.example/verify?x=1
https://phish.evil.example/second-path
""".strip()


def test_extract_hosts_dedupes_and_lowercases() -> None:
    hosts = _extract_hosts(
        "https://A.EXAMPLE/x\nhttps://a.example/y\nhttps://b.example/"
    )
    assert hosts == frozenset({"a.example", "b.example"})


def test_lookup_matches_host_in_feed() -> None:
    calls = []
    client = OpenPhishReputationClient(
        feed_fetcher=lambda: calls.append(1) or _FEED,
        time_source=FakeClock(),
    )

    match = client.lookup("phish.evil.example")
    miss = client.lookup("clean.example")

    assert match is not None
    assert match.provider_name == "openphish.com"
    assert match.confidence == 95.0
    assert miss is None
    assert len(calls) == 1  # feed fetched once, then reused


def test_feed_is_refreshed_after_ttl() -> None:
    clock = FakeClock()
    fetches = []

    def fetcher() -> str:
        fetches.append(1)
        return _FEED

    client = OpenPhishReputationClient(
        feed_fetcher=fetcher, refresh_seconds=100, time_source=clock
    )

    client.lookup("clean.example")
    clock.advance(50)
    client.lookup("clean.example")
    assert len(fetches) == 1  # still fresh

    clock.advance(60)  # now past TTL
    client.lookup("clean.example")
    assert len(fetches) == 2


def test_stale_snapshot_is_served_when_refresh_fails() -> None:
    clock = FakeClock()
    state = {"fail": False}

    def fetcher() -> str:
        if state["fail"]:
            raise ConnectionError("feed down")
        return _FEED

    client = OpenPhishReputationClient(
        feed_fetcher=fetcher, refresh_seconds=10, time_source=clock
    )

    assert client.lookup("phish.evil.example") is not None  # warm the cache
    state["fail"] = True
    clock.advance(20)  # force a refresh that will fail

    # Still answers from the stale snapshot instead of raising.
    assert client.lookup("phish.evil.example") is not None


def test_cold_start_failure_raises() -> None:
    def fetcher() -> str:
        raise ConnectionError("feed down")

    client = OpenPhishReputationClient(feed_fetcher=fetcher, time_source=FakeClock())

    with pytest.raises(ReputationLookupError):
        client.lookup("phish.evil.example")
