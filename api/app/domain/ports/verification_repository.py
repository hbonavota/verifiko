from abc import ABC, abstractmethod

from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
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
