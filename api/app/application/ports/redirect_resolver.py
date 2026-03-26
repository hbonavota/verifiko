from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RedirectHop:
    status_code: int
    source_url: str
    target_url: str


@dataclass(frozen=True, slots=True)
class RedirectResolution:
    final_url: str
    hops: tuple[RedirectHop, ...]
    provider_name: str


class RedirectResolutionError(Exception):
    """Raised when redirect resolution could not be completed reliably."""


class RedirectResolverPort(ABC):
    @abstractmethod
    def resolve(self, url: str) -> RedirectResolution:
        raise NotImplementedError
