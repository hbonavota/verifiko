from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)


@dataclass(slots=True)
class AggregatingReputationLookup(ReputationLookupPort):
    """Combines several reputation providers into a single consensus verdict.

    Policy:
    - Each provider is queried (in parallel when there is more than one).
    - If **every** provider is unavailable (circuit open or error), the whole
      lookup raises ``ReputationLookupError`` so the caller degrades coverage
      exactly as it would with a single failing provider.
    - When ``consensus_threshold`` or more distinct providers independently flag
      the host, the result is boosted to a high-confidence, terminal-grade match
      (two independent feeds agreeing is far stronger evidence than one).
    - A single flag is returned as-is, preserving each provider's own confidence
      (an authoritative feed stays authoritative; a weaker feed stays a signal,
      not a sentence).
    - No flags -> ``None``.
    """

    providers: tuple[ReputationLookupPort, ...]
    consensus_threshold: int = 2
    boosted_confidence: float = 99.0
    max_workers: int = 4
    _description_prefix: str = field(
        default="Independently flagged by multiple reputation providers", init=False
    )

    def lookup(self, hostname: str) -> ReputationMatch | None:
        available, matches = self._query_providers(hostname)
        if not available:
            raise ReputationLookupError("All reputation providers were unavailable.")
        if not matches:
            return None

        distinct_providers = sorted({match.provider_name for match in matches})
        if len(distinct_providers) >= self.consensus_threshold:
            return self._consensus_match(hostname, matches, distinct_providers)
        return max(matches, key=lambda match: match.confidence)

    def _query_providers(
        self, hostname: str
    ) -> tuple[bool, list[ReputationMatch]]:
        if len(self.providers) <= 1:
            results = [self._query_one(provider, hostname) for provider in self.providers]
        else:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(self.providers))) as pool:
                results = list(pool.map(lambda provider: self._query_one(provider, hostname), self.providers))

        any_available = False
        matches: list[ReputationMatch] = []
        for available, match in results:
            if not available:
                continue
            any_available = True
            if match is not None:
                matches.append(match)
        return any_available, matches

    @staticmethod
    def _query_one(
        provider: ReputationLookupPort, hostname: str
    ) -> tuple[bool, ReputationMatch | None]:
        try:
            return True, provider.lookup(hostname)
        except Exception:
            # A provider that errors or is short-circuited simply does not
            # contribute; it must never fail the whole aggregation.
            return False, None

    def _consensus_match(
        self,
        hostname: str,
        matches: list[ReputationMatch],
        distinct_providers: list[str],
    ) -> ReputationMatch:
        strongest = max(matches, key=lambda match: match.confidence)
        confidence = min(100.0, max(self.boosted_confidence, strongest.confidence))
        return ReputationMatch(
            queried_value=hostname,
            provider_name="; ".join(distinct_providers),
            confidence=confidence,
            reference_count=sum(match.reference_count for match in matches),
            match_scope=strongest.match_scope,
            description=(
                f"{self._description_prefix}: {', '.join(distinct_providers)}."
            ),
        )
