from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)

DEFAULT_OPENPHISH_FEED_URL = "https://openphish.com/feed.txt"


@dataclass(slots=True)
class OpenPhishReputationClient(ReputationLookupPort):
    """Keyless reputation provider backed by the OpenPhish community feed.

    The feed is a newline-separated list of phishing URLs. It is fetched at most
    once per ``refresh_seconds`` and reduced to a set of hostnames for O(1)
    membership checks. If a refresh fails but a previous snapshot exists, the
    stale snapshot is served rather than failing the lookup; only a cold start
    with no snapshot surfaces an error.

    Confidence defaults below the terminal-blacklist threshold so an OpenPhish
    hit on its own is a strong signal, while agreement with another feed is what
    escalates to a confirmed verdict via the aggregator's consensus policy.
    """

    feed_fetcher: Callable[[], str]
    refresh_seconds: float = 1800.0
    confidence: float = 95.0
    provider_name: str = "openphish.com"
    time_source: Callable[[], float] = time.monotonic
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _hosts: frozenset[str] | None = field(default=None, init=False, repr=False)
    _loaded_at: float | None = field(default=None, init=False, repr=False)

    def lookup(self, hostname: str) -> ReputationMatch | None:
        hosts = self._current_hosts()
        normalized = hostname.lower().strip(".")
        if normalized and normalized in hosts:
            return ReputationMatch(
                queried_value=hostname,
                provider_name=self.provider_name,
                confidence=self.confidence,
                reference_count=1,
                match_scope="host",
                description="Host is present in the OpenPhish community phishing feed.",
            )
        return None

    def _current_hosts(self) -> frozenset[str]:
        with self._lock:
            if self._hosts is not None and not self._is_stale():
                return self._hosts

            try:
                feed_text = self.feed_fetcher()
            except Exception as exc:
                if self._hosts is not None:
                    return self._hosts  # serve the last good snapshot
                raise ReputationLookupError(
                    f"OpenPhish feed could not be retrieved: {exc}"
                ) from exc

            self._hosts = _extract_hosts(feed_text)
            self._loaded_at = self.time_source()
            return self._hosts

    def _is_stale(self) -> bool:
        if self._loaded_at is None:
            return True
        return (self.time_source() - self._loaded_at) >= self.refresh_seconds


def _extract_hosts(feed_text: str) -> frozenset[str]:
    hosts: set[str] = set()
    for raw_line in feed_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        host = urlsplit(line).hostname
        if host:
            hosts.add(host.lower().strip("."))
    return frozenset(hosts)


def build_openphish_feed_fetcher(
    feed_url: str = DEFAULT_OPENPHISH_FEED_URL,
    timeout_seconds: float = 5.0,
) -> Callable[[], str]:
    """Returns a fetcher that downloads the OpenPhish feed over HTTPS."""

    def _fetch() -> str:
        request = Request(feed_url, headers={"User-Agent": "Verifiko/1.0"}, method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ReputationLookupError(str(exc)) from exc

    return _fetch
