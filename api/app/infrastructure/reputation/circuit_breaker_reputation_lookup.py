from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.reputation_lookup import (
    ReputationLookupPort,
    ReputationMatch,
)
from app.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
)


@dataclass(slots=True)
class CircuitBreakerReputationLookup(ReputationLookupPort):
    """Guards a single reputation provider with a circuit breaker.

    When the breaker is open the call is short-circuited with
    ``CircuitOpenError`` instead of hitting the provider. Provider exceptions are
    counted as failures and re-raised so the aggregator can decide how to treat
    an unavailable provider.
    """

    inner: ReputationLookupPort
    breaker: CircuitBreaker
    provider_name: str

    def lookup(self, hostname: str) -> ReputationMatch | None:
        if not self.breaker.allow():
            raise CircuitOpenError(f"{self.provider_name} reputation circuit is open")
        try:
            result = self.inner.lookup(hostname)
        except Exception:
            self.breaker.record_failure()
            raise
        self.breaker.record_success()
        return result
