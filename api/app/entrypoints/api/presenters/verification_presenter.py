from app.application.dto.verification_dto import VerificationDTO
from app.application.services.verification_text_localizer import (
    SupportedLocale,
    localize_verification_dto,
)
from app.entrypoints.api.schemas.verification_schema import VerificationResponse


class VerificationPresenter:
    @staticmethod
    def to_response(
        verification: VerificationDTO,
        locale: SupportedLocale = "en",
    ) -> VerificationResponse:
        localized = localize_verification_dto(verification, locale=locale)
        return VerificationResponse.model_validate(localized)
