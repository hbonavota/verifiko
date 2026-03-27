from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.exceptions.domain_exception import DomainException
from app.domain.i18n.resolver import resolve_message


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
            raise DomainException(resolve_message("error.invalid_verification_id")) from exc

    def __str__(self) -> str:
        return str(self.value)
