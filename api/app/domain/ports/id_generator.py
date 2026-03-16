from abc import ABC, abstractmethod

from app.domain.value_objects.verification_id import VerificationId


class IdGeneratorPort(ABC):
    @abstractmethod
    def next_verification_id(self) -> VerificationId:
        raise NotImplementedError
