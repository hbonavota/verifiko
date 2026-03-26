from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedAddress:
    ip_address: str
    reverse_hostname: str | None = None


@dataclass(frozen=True, slots=True)
class InfrastructureProfile:
    queried_host: str
    provider_name: str
    resolved_addresses: tuple[ResolvedAddress, ...]


class InfrastructureLookupError(Exception):
    """Raised when infrastructure intelligence could not be retrieved reliably."""


class InfrastructureLookupPort(ABC):
    @abstractmethod
    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        raise NotImplementedError
