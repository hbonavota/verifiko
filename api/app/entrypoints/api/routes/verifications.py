from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.queries.get_verification_query import GetVerificationQuery
from app.application.queries.list_verifications_query import ListVerificationsQuery
from app.application.services.message_resolver import resolve_message
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.application.use_cases.get_verification_result import GetVerificationResultUseCase
from app.application.use_cases.list_verifications import ListVerificationsUseCase
from app.entrypoints.api.dependencies.container import (
    get_create_url_verification_use_case,
    get_get_verification_result_use_case,
    get_list_verifications_use_case,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.presenters.verification_presenter import VerificationPresenter
from app.entrypoints.api.schemas.verification_schema import (
    CreateVerificationRequest,
    VerificationResponse,
)
from app.domain.enums.verification_status import VerificationStatus

router = APIRouter(prefix="/verifications", tags=["verifications"])


@router.post("", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(
    payload: CreateVerificationRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: CreateURLVerificationUseCase = Depends(get_create_url_verification_use_case),
) -> VerificationResponse:
    locale = select_response_locale(accept_language)
    if payload.signals:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=resolve_message(
                "error.client_supplied_signals_not_accepted",
                language=locale,
            ),
        )

    dto = use_case.execute(
        CreateVerificationCommand(
            url=payload.url,
        )
    )
    return VerificationPresenter.to_response(
        dto,
        locale=locale,
    )


@router.get("", response_model=list[VerificationResponse])
def list_verifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: VerificationStatus | None = Query(default=None),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: ListVerificationsUseCase = Depends(get_list_verifications_use_case),
) -> list[VerificationResponse]:
    dtos = use_case.execute(ListVerificationsQuery(limit=limit, offset=offset, status=status))
    locale = select_response_locale(accept_language)
    return [VerificationPresenter.to_response(dto, locale=locale) for dto in dtos]


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_verification(
    verification_id: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: GetVerificationResultUseCase = Depends(get_get_verification_result_use_case),
) -> VerificationResponse:
    dto = use_case.execute(GetVerificationQuery(verification_id=verification_id))
    return VerificationPresenter.to_response(
        dto,
        locale=select_response_locale(accept_language),
    )
