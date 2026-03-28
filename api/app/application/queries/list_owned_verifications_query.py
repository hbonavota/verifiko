from dataclasses import dataclass

from app.domain.enums.verification_status import VerificationStatus


@dataclass(frozen=True, slots=True)
class ListOwnedVerificationsQuery:
    owner_user_id: str
    limit: int = 50
    offset: int = 0
    status: VerificationStatus | None = None
