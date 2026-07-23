from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.enums.verification_job_status import VerificationJobStatus


@dataclass(slots=True)
class VerificationJob:
    """The asynchronous lifecycle of a single URL verification request.

    The heavy verification pipeline runs off the request path; this record tracks
    the job from acceptance through completion. When completed it points at the
    persisted verification via ``result_verification_id``.
    """

    id: str
    owner_user_id: str
    url: str
    status: VerificationJobStatus
    created_at: datetime
    updated_at: datetime
    result_verification_id: str | None = None
    error_message: str | None = None

    @staticmethod
    def queue(
        *,
        job_id: str,
        owner_user_id: str,
        url: str,
        now: datetime | None = None,
    ) -> "VerificationJob":
        moment = now or datetime.now(timezone.utc)
        return VerificationJob(
            id=job_id,
            owner_user_id=owner_user_id,
            url=url,
            status=VerificationJobStatus.QUEUED,
            created_at=moment,
            updated_at=moment,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in {VerificationJobStatus.COMPLETED, VerificationJobStatus.FAILED}

    def mark_running(self, now: datetime | None = None) -> None:
        self.status = VerificationJobStatus.RUNNING
        self.updated_at = now or datetime.now(timezone.utc)

    def mark_completed(self, verification_id: str, now: datetime | None = None) -> None:
        self.status = VerificationJobStatus.COMPLETED
        self.result_verification_id = verification_id
        self.error_message = None
        self.updated_at = now or datetime.now(timezone.utc)

    def mark_failed(self, error_message: str, now: datetime | None = None) -> None:
        self.status = VerificationJobStatus.FAILED
        self.error_message = error_message
        self.updated_at = now or datetime.now(timezone.utc)
