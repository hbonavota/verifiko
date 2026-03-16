from dataclasses import dataclass

from app.application.dto.verification_dto import VerificationDTO
from app.application.exceptions.application_exception import VerificationNotFoundError
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.queries.get_verification_query import GetVerificationQuery
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.verification_id import VerificationId


@dataclass(slots=True)
class GetVerificationResultUseCase:
    repository: VerificationRepository

    def execute(self, query: GetVerificationQuery) -> VerificationDTO:
        verification_id = VerificationId.from_string(query.verification_id)
        verification = self.repository.get_by_id(verification_id)
        if verification is None:
            raise VerificationNotFoundError(f"Verification not found: {query.verification_id}")
        return VerificationMapper.to_dto(verification)
