from app.application.dto.verification_dto import VerificationDTO
from app.entrypoints.api.schemas.verification_schema import VerificationResponse


class VerificationPresenter:
    @staticmethod
    def to_response(verification: VerificationDTO) -> VerificationResponse:
        return VerificationResponse.model_validate(verification)
