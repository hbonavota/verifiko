from dataclasses import dataclass

from app.application.dto.verification_dto import VerificationDTO
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.queries.list_verifications_query import ListVerificationsQuery
from app.domain.ports.verification_repository import VerificationRepository


@dataclass(slots=True)
class ListVerificationsUseCase:
    repository: VerificationRepository

    def execute(self, query: ListVerificationsQuery) -> list[VerificationDTO]:
        verifications = self.repository.list(
            limit=query.limit,
            offset=query.offset,
            status=query.status,
        )
        return [
            VerificationMapper.to_dto(verification) for verification in verifications
        ]
