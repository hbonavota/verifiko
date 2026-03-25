from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TlsValidationResult:
    is_valid: bool
    provider_name: str
    failure_reason: str | None = None


class TlsValidationError(Exception):
    """Raised when TLS validation could not be completed reliably."""


class TlsValidatorPort(ABC):
    @abstractmethod
    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        raise NotImplementedError
