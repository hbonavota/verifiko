from app.application.commands.create_verification_command import CreateVerificationCommand, SignalInput
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.domain.entities.verification import Verification
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.value_objects.verification_id import VerificationId


class FakeRepository(VerificationRepository):
    def __init__(self) -> None:
        self._items: list[Verification] = []

    def save(self, verification: Verification) -> Verification:
        self._items.append(verification)
        return verification

    def get_by_id(self, verification_id: VerificationId) -> Verification | None:
        for item in self._items:
            if item.id == verification_id:
                return item
        return None

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        items = self._items
        if status is not None:
            items = [item for item in items if item.status == status]
        return items[offset : offset + limit]


class FakeIdGenerator(IdGeneratorPort):
    def next_verification_id(self) -> VerificationId:
        return VerificationId.from_string("550e8400-e29b-41d4-a716-446655440000")


def test_create_url_verification_use_case() -> None:
    use_case = CreateURLVerificationUseCase(
        repository=FakeRepository(),
        id_generator=FakeIdGenerator(),
        scoring_service=RiskScoringEngine(),
    )

    dto = use_case.execute(
        CreateVerificationCommand(
            url="verifiko.es/login",
            signals=(
                SignalInput(
                    signal_type=SignalType.BRAND_IMPERSONATION,
                    category=SignalCategory.CONTENT_BEHAVIOR,
                    severity=SignalSeverity.HIGH,
                    confidence=92,
                    title="Brand impersonation",
                    description="Brand style copied",
                    source="content-analyzer",
                ),
            ),
        )
    )

    assert dto.id == "550e8400-e29b-41d4-a716-446655440000"
    assert dto.status == "COMPLETED"
    assert dto.risk_assessment is not None
