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
        screenshot_url: str | None = None,
    ) -> VerificationResponse:
        localized = localize_verification_dto(verification, locale=locale)
        response = VerificationResponse.model_validate(localized)
        if screenshot_url is not None:
            response = response.model_copy(update={"screenshot_url": screenshot_url})
        return response
