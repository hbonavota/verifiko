from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.application.exceptions.application_exception import (
    VerificationNotFoundError,
    VerificationScanNotFoundError,
)
from app.application.queries.get_owned_verification_query import GetOwnedVerificationQuery
from app.application.services.message_resolver import resolve_message
from app.application.use_cases.get_owned_verification_result import GetOwnedVerificationResultUseCase
from app.application.ports.screenshot_store import ScreenshotStorePort
from app.application.use_cases.get_verification_scan import GetVerificationScanUseCase
from app.application.use_cases.submit_verification_scan import SubmitVerificationScanUseCase
from app.domain.entities.user import User
from app.domain.entities.verification_job import VerificationJob
from app.entrypoints.api.dependencies.auth import get_current_user
from app.entrypoints.api.dependencies.container import (
    get_get_owned_verification_result_use_case,
    get_get_verification_scan_use_case,
    get_screenshot_store,
    get_submit_verification_scan_use_case,
)
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.presenters.verification_presenter import VerificationPresenter
from app.entrypoints.api.schemas.scan_schema import (
    ScanAcceptedResponse,
    ScanBatchAcceptedResponse,
    ScanResponse,
    SubmitScanBatchRequest,
    SubmitScanRequest,
)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_scan(
    payload: SubmitScanRequest,
    current_user: User = Depends(get_current_user),
    use_case: SubmitVerificationScanUseCase = Depends(get_submit_verification_scan_use_case),
) -> ScanAcceptedResponse:
    job = use_case.execute(
        owner_user_id=str(current_user.id),
        url=payload.url,
        webhook_url=payload.webhook_url,
    )
    return _accepted(job)


@router.post("/batch", response_model=ScanBatchAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_scan_batch(
    payload: SubmitScanBatchRequest,
    current_user: User = Depends(get_current_user),
    use_case: SubmitVerificationScanUseCase = Depends(get_submit_verification_scan_use_case),
) -> ScanBatchAcceptedResponse:
    jobs = use_case.execute_batch(
        owner_user_id=str(current_user.id),
        urls=list(payload.urls),
        webhook_url=payload.webhook_url,
    )
    return ScanBatchAcceptedResponse(scans=tuple(_accepted(job) for job in jobs))


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    current_user: User = Depends(get_current_user),
    use_case: GetVerificationScanUseCase = Depends(get_get_verification_scan_use_case),
    verification_use_case: GetOwnedVerificationResultUseCase = Depends(
        get_get_owned_verification_result_use_case
    ),
    screenshot_store: ScreenshotStorePort = Depends(get_screenshot_store),
) -> ScanResponse:
    locale = select_response_locale(accept_language)
    try:
        job = use_case.execute(scan_id, str(current_user.id))
    except VerificationScanNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resolve_message("error.verification_scan_not_found", language=locale),
        ) from exc

    # Mint a short-lived presigned URL from the durable key at read time; it is
    # never stored. The no-op store (screenshots disabled) yields None.
    screenshot_url = (
        screenshot_store.presigned_url(job.screenshot_ref)
        if job.screenshot_ref
        else None
    )

    result = None
    if job.result_verification_id is not None:
        try:
            dto = verification_use_case.execute(
                GetOwnedVerificationQuery(
                    verification_id=job.result_verification_id,
                    owner_user_id=str(current_user.id),
                )
            )
            result = VerificationPresenter.to_response(
                dto, locale=locale, screenshot_url=screenshot_url
            )
        except VerificationNotFoundError:
            result = None

    return ScanResponse(
        scan_id=job.id,
        status=job.status.value.lower(),
        url=job.url,
        created_at=_iso(job.created_at),
        updated_at=_iso(job.updated_at),
        result_verification_id=job.result_verification_id,
        result=result,
        error=job.error_message,
        screenshot_url=screenshot_url,
    )


def _accepted(job: VerificationJob) -> ScanAcceptedResponse:
    return ScanAcceptedResponse(scan_id=job.id, status=job.status.value.lower(), url=job.url)


def _iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
