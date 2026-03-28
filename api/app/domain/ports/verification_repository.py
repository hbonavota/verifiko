from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
from app.domain.value_objects.user_id import UserId
from app.domain.value_objects.verification_id import VerificationId


class VerificationRepository(ABC):
    @abstractmethod
    def save(self, verification: Verification) -> Verification:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, verification_id: VerificationId) -> Verification | None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        raise NotImplementedError

    def get_by_id_for_owner(
        self,
        verification_id: VerificationId,
        owner_user_id: UserId,
    ) -> Verification | None:
        verification = self.get_by_id(verification_id)
        if verification is None or verification.user_id != owner_user_id:
            return None
        return verification

    def list_for_owner(
        self,
        owner_user_id: UserId,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        items = self.list(limit=max(limit + offset, limit), offset=0, status=status)
        owned_items = [item for item in items if item.user_id == owner_user_id]
        return owned_items[offset : offset + limit]
