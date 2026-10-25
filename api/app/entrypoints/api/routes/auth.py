from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.application.dto.user_dto import AuthSessionDTO
from app.application.ports.google_identity_verifier import (
    GoogleIdentityVerificationError,
    GoogleIdentityVerificationUnavailableError,
)
from app.application.services.message_resolver import resolve_message
from app.application.use_cases.authenticate_with_email_password import (
    AuthenticateWithEmailPasswordCommand,
    AuthenticateWithEmailPasswordUseCase,
    InvalidEmailPasswordCredentialsError,
)
from app.application.use_cases.authenticate_with_google import (
    AuthenticateWithGoogleUseCase,
)
from app.application.use_cases.authenticate_with_magic_link import (
    AuthenticateWithMagicLinkUseCase,
    InvalidMagicLinkError,
)
from app.application.use_cases.register_with_email_password import (
    EmailAlreadyRegisteredError,
    RegisterWithEmailPasswordCommand,
    RegisterWithEmailPasswordUseCase,
)
from app.application.use_cases.request_magic_link import RequestMagicLinkUseCase
from app.entrypoints.api.client_ip import resolve_client_ip
from app.entrypoints.api.dependencies.container import (
    get_authenticate_with_email_password_use_case,
    get_authenticate_with_google_use_case,
    get_authenticate_with_magic_link_use_case,
    get_magic_link_request_rate_limiter,
    get_register_with_email_password_use_case,
    get_request_magic_link_use_case,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.schemas.auth_schema import (
    AuthSessionResponse,
    GoogleAuthRequest,
    LocalLoginRequest,
    LocalRegisterRequest,
    MagicLinkConsumeRequest,
    MagicLinkRequest,
    MagicLinkRequestResponse,
    UserResponse,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.fixed_window_rate_limiter import FixedWindowRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=AuthSessionResponse)
def authenticate_with_google(
    payload: GoogleAuthRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: AuthenticateWithGoogleUseCase = Depends(
        get_authenticate_with_google_use_case
    ),
) -> AuthSessionResponse:
    locale = select_response_locale(accept_language)
    try:
        session = use_case.execute(payload.id_token)
    except GoogleIdentityVerificationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=resolve_message(
                "error.google_authentication_not_configured",
                language=locale,
            ),
        ) from exc
    except GoogleIdentityVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=resolve_message(
                "error.google_identity_token_invalid",
                language=locale,
            ),
        ) from exc

    return _session_response(session)


@router.post(
    "/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED
)
def register_with_email_password(
    payload: LocalRegisterRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: RegisterWithEmailPasswordUseCase = Depends(
        get_register_with_email_password_use_case
    ),
) -> AuthSessionResponse:
    locale = select_response_locale(accept_language)
    try:
        session = use_case.execute(
            RegisterWithEmailPasswordCommand(
                email=payload.email,
                password=payload.password,
                display_name=payload.display_name,
            )
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=resolve_message("error.email_already_registered", language=locale),
        ) from exc

    return _session_response(session)


@router.post("/login", response_model=AuthSessionResponse)
def authenticate_with_email_password(
    payload: LocalLoginRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: AuthenticateWithEmailPasswordUseCase = Depends(
        get_authenticate_with_email_password_use_case
    ),
) -> AuthSessionResponse:
    locale = select_response_locale(accept_language)
    try:
        session = use_case.execute(
            AuthenticateWithEmailPasswordCommand(
                email=payload.email,
                password=payload.password,
            )
        )
    except InvalidEmailPasswordCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=resolve_message(
                "error.local_auth_invalid_credentials", language=locale
            ),
        ) from exc

    return _session_response(session)


@router.post(
    "/magic-link/request",
    response_model=MagicLinkRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_magic_link(
    request: Request,
    payload: MagicLinkRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: RequestMagicLinkUseCase = Depends(get_request_magic_link_use_case),
    rate_limiter: FixedWindowRateLimiter = Depends(get_magic_link_request_rate_limiter),
) -> MagicLinkRequestResponse:
    locale = select_response_locale(accept_language)
    client_key = resolve_client_ip(
        request, trusted_proxy_networks=get_settings().trusted_proxy_networks
    )
    retry_after = rate_limiter.check(client_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=resolve_message("error.magic_link_rate_limited", language=locale),
            headers={"Retry-After": str(retry_after)},
        )
    # Always succeeds silently: the link both signs in and creates accounts, so
    # the response never reveals whether the email already exists.
    use_case.execute(payload.email)
    return MagicLinkRequestResponse()


@router.post("/magic-link/consume", response_model=AuthSessionResponse)
def consume_magic_link(
    payload: MagicLinkConsumeRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: AuthenticateWithMagicLinkUseCase = Depends(
        get_authenticate_with_magic_link_use_case
    ),
) -> AuthSessionResponse:
    locale = select_response_locale(accept_language)
    try:
        session = use_case.execute(payload.token)
    except InvalidMagicLinkError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=resolve_message("error.magic_link_invalid", language=locale),
        ) from exc
    return _session_response(session)


def _session_response(session: AuthSessionDTO) -> AuthSessionResponse:
    return AuthSessionResponse(
        access_token=session.access_token,
        token_type=session.token_type,
        user=UserResponse.model_validate(session.user),
    )
