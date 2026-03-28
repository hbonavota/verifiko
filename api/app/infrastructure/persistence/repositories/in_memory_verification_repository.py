from __future__ import annotations

from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.user_id import UserId
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
        items = sorted(self._items, key=lambda item: item.created_at, reverse=True)
        if status is not None:
            items = [item for item in items if item.status is status]
        return items[offset : offset + limit]

    def get_by_id_for_owner(
        self,
        verification_id: VerificationId,
        owner_user_id: UserId,
    ) -> Verification | None:
        for item in self._items:
            if item.id == verification_id and item.user_id == owner_user_id:
                return item
        return None

    def list_for_owner(
        self,
        owner_user_id: UserId,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        items = sorted(self._items, key=lambda item: item.created_at, reverse=True)
        items = [item for item in items if item.user_id == owner_user_id]
        if status is not None:
            items = [item for item in items if item.status is status]
        return items[offset : offset + limit]

    def clear(self) -> None:
        self._items.clear()
