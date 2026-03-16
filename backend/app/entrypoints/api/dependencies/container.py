from functools import lru_cache

from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.application.use_cases.get_verification_result import GetVerificationResultUseCase
from app.application.use_cases.list_verifications import ListVerificationsUseCase
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.infrastructure.ids.id_generator import UUIDVerificationIdGenerator
from app.infrastructure.persistence.repositories.in_memory_verification_repository import (
    InMemoryVerificationRepository,
)


@lru_cache(maxsize=1)
def get_verification_repository() -> InMemoryVerificationRepository:
    return InMemoryVerificationRepository()


@lru_cache(maxsize=1)
def get_id_generator() -> UUIDVerificationIdGenerator:
    return UUIDVerificationIdGenerator()


@lru_cache(maxsize=1)
def get_risk_scoring_engine() -> RiskScoringEngine:
    return RiskScoringEngine()


def get_create_url_verification_use_case() -> CreateURLVerificationUseCase:
    return CreateURLVerificationUseCase(
        repository=get_verification_repository(),
        id_generator=get_id_generator(),
        scoring_service=get_risk_scoring_engine(),
    )


def get_get_verification_result_use_case() -> GetVerificationResultUseCase:
    return GetVerificationResultUseCase(repository=get_verification_repository())


def get_list_verifications_use_case() -> ListVerificationsUseCase:
    return ListVerificationsUseCase(repository=get_verification_repository())
