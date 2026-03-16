from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.exceptions.domain_exception import DomainException


@dataclass(frozen=True, slots=True)
class VerificationId:
    value: UUID

    @staticmethod
    def new() -> "VerificationId":
        return VerificationId(value=uuid4())

    @staticmethod
    def from_string(raw: str) -> "VerificationId":
        try:
            return VerificationId(value=UUID(raw))
        except ValueError as exc:
            raise DomainException("Invalid verification id.") from exc

    def __str__(self) -> str:
        return str(self.value)
