from dataclasses import dataclass

from app.application.dto.verification_dto import VerificationDTO
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.queries.list_owned_verifications_query import (
    ListOwnedVerificationsQuery,
)
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class ListOwnedVerificationsUseCase:
    repository: VerificationRepository

    def execute(self, query: ListOwnedVerificationsQuery) -> list[VerificationDTO]:
        verifications = self.repository.list_for_owner(
            owner_user_id=UserId.from_string(query.owner_user_id),
            limit=query.limit,
            offset=query.offset,
            status=query.status,
        )
        return [
            VerificationMapper.to_dto(verification) for verification in verifications
        ]
