from fastapi import APIRouter, Depends, Query, status

from app.application.commands.create_verification_command import CreateVerificationCommand, SignalInput
from app.application.queries.get_verification_query import GetVerificationQuery
from app.application.queries.list_verifications_query import ListVerificationsQuery
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.application.use_cases.get_verification_result import GetVerificationResultUseCase
from app.application.use_cases.list_verifications import ListVerificationsUseCase
from app.entrypoints.api.dependencies.container import (
    get_create_url_verification_use_case,
    get_get_verification_result_use_case,
    get_list_verifications_use_case,
)
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
    use_case: CreateURLVerificationUseCase = Depends(get_create_url_verification_use_case),
) -> VerificationResponse:
    dto = use_case.execute(
        CreateVerificationCommand(
            url=payload.url,
            signals=tuple(
                SignalInput(
                    signal_type=signal.signal_type,
                    category=signal.category,
                    severity=signal.severity,
                    confidence=signal.confidence,
                    title=signal.title,
                    description=signal.description,
                    source=signal.source,
                    evidence=signal.evidence,
                    tags=signal.tags,
                )
                for signal in payload.signals
            ),
        )
    )
    return VerificationPresenter.to_response(dto)


@router.get("", response_model=list[VerificationResponse])
def list_verifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: VerificationStatus | None = Query(default=None),
    use_case: ListVerificationsUseCase = Depends(get_list_verifications_use_case),
) -> list[VerificationResponse]:
    dtos = use_case.execute(ListVerificationsQuery(limit=limit, offset=offset, status=status))
    return [VerificationPresenter.to_response(dto) for dto in dtos]


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_verification(
    verification_id: str,
    use_case: GetVerificationResultUseCase = Depends(get_get_verification_result_use_case),
) -> VerificationResponse:
    dto = use_case.execute(GetVerificationQuery(verification_id=verification_id))
    return VerificationPresenter.to_response(dto)
