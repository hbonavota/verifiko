from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.verification_id import VerificationId


class InMemoryVerificationRepository(VerificationRepository):
    def __init__(self) -> None:
        self._items: list[Verification] = []

    def save(self, verification: Verification) -> Verification:
        for index, existing in enumerate(self._items):
            if existing.id == verification.id:
                self._items[index] = verification
                return verification

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
            items = [item for item in items if item.status is status]
        return items[offset : offset + limit]

    def clear(self) -> None:
        self._items.clear()
