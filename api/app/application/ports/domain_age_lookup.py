from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DomainRegistrationInfo:
    registered_at: datetime
    provider_name: str


class DomainRegistrationLookupError(Exception):
    """Raised when domain registration metadata cannot be retrieved reliably."""


class DomainAgeLookupPort(ABC):
    @abstractmethod
    def lookup(self, domain: str) -> DomainRegistrationInfo | None:
        raise NotImplementedError
