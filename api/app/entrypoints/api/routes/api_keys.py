from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.application.exceptions.application_exception import ApiKeyNotFoundError
from app.application.services.message_resolver import resolve_message
from app.application.use_cases.create_api_key import CreateApiKeyCommand, CreateApiKeyUseCase
from app.application.use_cases.list_api_keys import ListApiKeysUseCase
from app.application.use_cases.revoke_api_key import RevokeApiKeyCommand, RevokeApiKeyUseCase
from app.domain.entities.user import User
from app.entrypoints.api.dependencies.auth import get_current_user
from app.entrypoints.api.dependencies.container import (
    get_create_api_key_use_case,
    get_list_api_keys_use_case,
    get_revoke_api_key_use_case,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.schemas.api_key_schema import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreatedApiKeyResponse,
)

router = APIRouter(prefix="/keys", tags=["api-keys"])


@router.post("", response_model=CreatedApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    use_case: CreateApiKeyUseCase = Depends(get_create_api_key_use_case),
) -> CreatedApiKeyResponse:
    created = use_case.execute(
        CreateApiKeyCommand(user_id=current_user.id, name=payload.name)
    )
    return CreatedApiKeyResponse(
        id=created.api_key.id,
        name=created.api_key.name,
        token_prefix=created.api_key.token_prefix,
        created_at=created.api_key.created_at,
        api_key=created.plaintext,
    )


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
) -> list[ApiKeyResponse]:
    return [ApiKeyResponse.model_validate(dto) for dto in use_case.execute(current_user.id)]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    current_user: User = Depends(get_current_user),
    use_case: RevokeApiKeyUseCase = Depends(get_revoke_api_key_use_case),
) -> Response:
    try:
        use_case.execute(
            RevokeApiKeyCommand(user_id=current_user.id, api_key_id=key_id)
        )
    except ApiKeyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resolve_message(
                "error.api_key_not_found",
                language=select_response_locale(accept_language),
            ),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
