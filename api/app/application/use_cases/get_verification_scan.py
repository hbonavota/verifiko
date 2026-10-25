from dataclasses import dataclass

from app.application.exceptions.application_exception import (
    VerificationScanNotFoundError,
)
from app.domain.entities.verification_job import VerificationJob
from app.domain.ports.verification_job_store import VerificationJobStore


@dataclass(slots=True)
class GetVerificationScanUseCase:
    job_store: VerificationJobStore

    def execute(self, job_id: str, owner_user_id: str) -> VerificationJob:
        job = self.job_store.get_for_owner(job_id, owner_user_id)
        # Ownership doubles as a non-enumeration guard: another owner's scan is
        # indistinguishable from a missing one.
        if job is None:
            raise VerificationScanNotFoundError(job_id)
        return job
