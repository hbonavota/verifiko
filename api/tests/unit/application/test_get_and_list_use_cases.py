from app.application.queries.get_verification_query import GetVerificationQuery
from app.application.queries.list_verifications_query import ListVerificationsQuery
from app.application.use_cases.get_verification_result import (
    GetVerificationResultUseCase,
)
from app.application.use_cases.list_verifications import ListVerificationsUseCase
from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.verification_id import VerificationId


class InMemoryRepository(VerificationRepository):
    def __init__(self, items: list[Verification]) -> None:
        self._items = items

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


def test_get_and_list_use_cases() -> None:
    verification = Verification.create_url(
        "https://example.org",
        verification_id=VerificationId.from_string(
            "550e8400-e29b-41d4-a716-446655440001"
        ),
    )

    repository = InMemoryRepository([verification])

    get_result = GetVerificationResultUseCase(repository).execute(
        GetVerificationQuery(verification_id="550e8400-e29b-41d4-a716-446655440001")
    )
    listed = ListVerificationsUseCase(repository).execute(
        ListVerificationsQuery(limit=10, offset=0)
    )

    assert get_result.id == "550e8400-e29b-41d4-a716-446655440001"
    assert len(listed) == 1
