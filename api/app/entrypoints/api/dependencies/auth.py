from fastapi import Depends, Header, HTTPException, status

from app.application.ports.auth_token_service import (
    AuthTokenError,
    AuthTokenServicePort,
)
from app.application.services.message_resolver import resolve_message
from app.application.use_cases.authenticate_with_api_key import (
    AuthenticateWithApiKeyUseCase,
)
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository
from app.entrypoints.api.dependencies.container import (
    get_auth_token_service,
    get_authenticate_with_api_key_use_case,
    get_user_repository,
)
from app.entrypoints.api.locale import select_response_locale
from app.infrastructure.security.sha256_api_key_token_service import API_KEY_PREFIX


def get_optional_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    auth_token_service: AuthTokenServicePort = Depends(get_auth_token_service),
    user_repository: UserRepository = Depends(get_user_repository),
    api_key_authenticator: AuthenticateWithApiKeyUseCase = Depends(
        get_authenticate_with_api_key_use_case
    ),
) -> User | None:
    presented_api_key = _extract_presented_api_key(authorization, x_api_key)
    if presented_api_key is not None:
        user = api_key_authenticator.execute(presented_api_key)
        if user is None:
            raise _authentication_error(accept_language)
        return user

    if authorization is None:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _authentication_error(accept_language)

    try:
        user_id = auth_token_service.resolve_user_id(token)
    except AuthTokenError as exc:
        raise _authentication_error(accept_language) from exc

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise _authentication_error(accept_language)
    return user


def _extract_presented_api_key(
    authorization: str | None,
    x_api_key: str | None,
) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.startswith(API_KEY_PREFIX):
            return token.strip()
    return None


def get_current_user(
    user: User | None = Depends(get_optional_current_user),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=resolve_message(
                "error.authentication_required",
                language=select_response_locale(accept_language),
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _authentication_error(accept_language: str | None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=resolve_message(
            "error.invalid_authentication_token",
            language=select_response_locale(accept_language),
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )
