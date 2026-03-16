from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.value_objects.verification_id import VerificationId


class UUIDVerificationIdGenerator(IdGeneratorPort):
    def next_verification_id(self) -> VerificationId:
        return VerificationId.new()
