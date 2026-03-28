from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.services.message_resolver import resolve_message
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.entrypoints.api.dependencies.container import (
    get_create_verification_rate_limiter,
    get_create_url_verification_use_case,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.presenters.verification_presenter import VerificationPresenter
from app.entrypoints.api.schemas.verification_schema import (
    CreateVerificationRequest,
    VerificationResponse,
)
from app.infrastructure.security.fixed_window_rate_limiter import FixedWindowRateLimiter

router = APIRouter(prefix="/verifications", tags=["verifications"])


@router.post("", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(
    request: Request,
    payload: CreateVerificationRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    use_case: CreateURLVerificationUseCase = Depends(get_create_url_verification_use_case),
    rate_limiter: FixedWindowRateLimiter = Depends(get_create_verification_rate_limiter),
) -> VerificationResponse:
    locale = select_response_locale(accept_language)
    retry_after = rate_limiter.check(_client_rate_limit_key(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=resolve_message(
                "error.verification_rate_limit_exceeded",
                language=locale,
            ),
            headers={"Retry-After": str(retry_after)},
        )
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
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> list[VerificationResponse]:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=resolve_message(
            "error.public_verification_history_disabled",
            language=select_response_locale(accept_language),
        ),
    )


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_verification(
    verification_id: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> VerificationResponse:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=resolve_message(
            "error.public_verification_retrieval_disabled",
            {"verification_id": verification_id},
            language=select_response_locale(accept_language),
        ),
    )


def _client_rate_limit_key(request: Request) -> str:
    client = request.client
    if client is None or not client.host:
        return "anonymous"
    return client.host
