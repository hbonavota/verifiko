from fastapi import APIRouter, Depends, Header, Query

from app.application.mappers.user_mapper import UserMapper
from app.application.queries.list_owned_verifications_query import (
    ListOwnedVerificationsQuery,
)
from app.application.use_cases.list_owned_verifications import (
    ListOwnedVerificationsUseCase,
)
from app.domain.entities.user import User
from app.entrypoints.api.dependencies.auth import get_current_user
from app.entrypoints.api.dependencies.container import (
    get_list_owned_verifications_use_case,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.presenters.verification_presenter import VerificationPresenter
from app.entrypoints.api.schemas.auth_schema import UserResponse
from app.entrypoints.api.schemas.verification_schema import VerificationResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserResponse)
def get_current_account(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(UserMapper.to_dto(current_user))


@router.get("/verifications", response_model=list[VerificationResponse])
def list_my_verifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    current_user: User = Depends(get_current_user),
    use_case: ListOwnedVerificationsUseCase = Depends(
        get_list_owned_verifications_use_case
    ),
) -> list[VerificationResponse]:
    locale = select_response_locale(accept_language)
    results = use_case.execute(
        ListOwnedVerificationsQuery(
            owner_user_id=str(current_user.id),
            limit=limit,
            offset=offset,
        )
    )
    return [
        VerificationPresenter.to_response(result, locale=locale) for result in results
    ]
