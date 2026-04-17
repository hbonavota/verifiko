from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.queries.get_owned_verification_query import GetOwnedVerificationQuery
from app.application.services.message_resolver import resolve_message
from app.application.services.quota_status_service import QuotaStatusService
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.application.use_cases.get_owned_verification_result import GetOwnedVerificationResultUseCase
from app.domain.entities.user import User
from app.entrypoints.api.dependencies.auth import get_current_user, get_optional_current_user
from app.entrypoints.api.dependencies.container import (
    get_authenticated_verification_rate_limiter,
    get_create_verification_rate_limiter,
    get_create_url_verification_use_case,
    get_get_owned_verification_result_use_case,
    get_quota_status_service,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.presenters.verification_presenter import VerificationPresenter
from app.entrypoints.api.schemas.verification_schema import (
    CreateVerificationRequest,
    VerificationResponse,
)
from app.entrypoints.api.schemas.quota_schema import QuotaStatusResponse
from app.infrastructure.security.authenticated_utc_day_quota_limiter import (
    AuthenticatedUtcDayQuotaLimiter,
)
from app.infrastructure.security.utc_day_quota_limiter import UtcDayQuotaLimiter

router = APIRouter(prefix="/verifications", tags=["verifications"])


@router.post("", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(
    request: Request,
    response: Response,
    payload: CreateVerificationRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    current_user: User | None = Depends(get_optional_current_user),
    use_case: CreateURLVerificationUseCase = Depends(get_create_url_verification_use_case),
    rate_limiter: UtcDayQuotaLimiter = Depends(get_create_verification_rate_limiter),
    authenticated_rate_limiter: AuthenticatedUtcDayQuotaLimiter = Depends(
        get_authenticated_verification_rate_limiter
    ),
) -> VerificationResponse:
    locale = select_response_locale(accept_language)
    if current_user is None:
        subject_key = _client_rate_limit_key(request)
        retry_after = rate_limiter.check(subject_key)
        quota_status = rate_limiter.get_status(subject_key)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=resolve_message(
                    "error.anonymous_daily_verification_limit_exceeded",
                    language=locale,
                ),
                headers={
                    "Retry-After": str(retry_after),
                    **_rate_limit_headers(quota_status),
                },
            )
    else:
        retry_after = authenticated_rate_limiter.check(current_user)
        quota_status = authenticated_rate_limiter.get_status(current_user)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=resolve_message(
                    "error.authenticated_daily_limit_exceeded",
                    language=locale,
                ),
                headers={
                    "Retry-After": str(retry_after),
                    **_rate_limit_headers(quota_status),
                },
            )
    response.headers.update(_rate_limit_headers(quota_status))
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
            user_id=current_user.id if current_user is not None else None,
        )
    )
    return VerificationPresenter.to_response(
        dto,
        locale=locale,
    )


@router.get("/quota-status", response_model=QuotaStatusResponse)
def get_quota_status(
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    quota_status_service: QuotaStatusService = Depends(get_quota_status_service),
) -> QuotaStatusResponse:
    if current_user is None:
        status = quota_status_service.for_anonymous(_client_rate_limit_key(request))
    else:
        status = quota_status_service.for_user(current_user)
    return QuotaStatusResponse(
        subject_type=status.subject_type,
        is_authenticated=status.is_authenticated,
        plan=status.plan,
        daily_limit=status.daily_limit,
        used_today=status.used_today,
        remaining_today=status.remaining_today,
        reset_at_utc=status.reset_at_utc,
        reset_in_seconds=status.reset_in_seconds,
        blocked=status.blocked,
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
    current_user: User = Depends(get_current_user),
    use_case: GetOwnedVerificationResultUseCase = Depends(get_get_owned_verification_result_use_case),
) -> VerificationResponse:
    locale = select_response_locale(accept_language)
    result = use_case.execute(
        GetOwnedVerificationQuery(
            verification_id=verification_id,
            owner_user_id=str(current_user.id),
        )
    )
    return VerificationPresenter.to_response(result, locale=locale)


def _client_rate_limit_key(request: Request) -> str:
    client = request.client
    if client is None or not client.host:
        return "anonymous"
    return client.host


def _rate_limit_headers(quota_status) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(quota_status.daily_limit),
        "X-RateLimit-Remaining": str(quota_status.remaining_today),
        "X-RateLimit-Reset": str(int(quota_status.reset_at_utc.timestamp())),
    }
