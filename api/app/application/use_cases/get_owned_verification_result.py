from dataclasses import dataclass

from app.application.dto.verification_dto import VerificationDTO
from app.application.exceptions.application_exception import VerificationNotFoundError
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.queries.get_owned_verification_query import (
    GetOwnedVerificationQuery,
)
from app.domain.i18n.resolver import resolve_message
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.user_id import UserId
from app.domain.value_objects.verification_id import VerificationId


@dataclass(slots=True)
class GetOwnedVerificationResultUseCase:
    repository: VerificationRepository

    def execute(self, query: GetOwnedVerificationQuery) -> VerificationDTO:
        verification = self.repository.get_by_id_for_owner(
            VerificationId.from_string(query.verification_id),
            UserId.from_string(query.owner_user_id),
        )
        if verification is None:
            raise VerificationNotFoundError(
                resolve_message(
                    "error.verification_not_found",
                    {"verification_id": query.verification_id},
                )
            )
        return VerificationMapper.to_dto(verification)
