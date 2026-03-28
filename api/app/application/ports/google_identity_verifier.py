from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    subject: str
    email: str
    display_name: str
    avatar_url: str | None


class GoogleIdentityVerificationError(Exception):
    """Raised when a Google identity token cannot be verified."""


class GoogleIdentityVerificationUnavailableError(Exception):
    """Raised when Google identity verification is not configured."""


class GoogleIdentityVerifierPort(ABC):
    @abstractmethod
    def verify(self, id_token: str) -> GoogleIdentity:
        raise NotImplementedError
