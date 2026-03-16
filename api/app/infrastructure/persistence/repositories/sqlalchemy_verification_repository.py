from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.verification_id import VerificationId


class SQLAlchemyVerificationRepository(VerificationRepository):
    def save(self, verification: Verification) -> Verification:
        raise NotImplementedError("SQLAlchemy persistence is not wired yet.")

    def get_by_id(self, verification_id: VerificationId) -> Verification | None:
        raise NotImplementedError("SQLAlchemy persistence is not wired yet.")

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        raise NotImplementedError("SQLAlchemy persistence is not wired yet.")
