from fastapi import Depends, Header, HTTPException, status

from app.application.ports.auth_token_service import AuthTokenError, AuthTokenServicePort
from app.application.services.message_resolver import resolve_message
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository
from app.entrypoints.api.dependencies.container import get_auth_token_service, get_user_repository
from app.entrypoints.api.locale import select_response_locale


def get_optional_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    auth_token_service: AuthTokenServicePort = Depends(get_auth_token_service),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User | None:
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
