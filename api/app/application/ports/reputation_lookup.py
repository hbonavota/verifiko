from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReputationMatch:
    queried_value: str
    provider_name: str
    confidence: float
    reference_count: int
    match_scope: str
    description: str


class ReputationLookupError(Exception):
    """Raised when reputation intelligence could not be retrieved reliably."""


class ReputationLookupPort(ABC):
    @abstractmethod
    def lookup(self, hostname: str) -> ReputationMatch | None:
        raise NotImplementedError
