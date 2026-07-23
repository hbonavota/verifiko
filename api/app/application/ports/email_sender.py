from abc import ABC, abstractmethod
from dataclasses import dataclass


class EmailDeliveryError(Exception):
    """Raised when an email could not be handed off to the provider."""


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str


class EmailSenderPort(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        raise NotImplementedError
