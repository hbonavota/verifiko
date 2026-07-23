import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.ports.verification_job_dispatcher import VerificationJobDispatcher
from app.domain.entities.verification_job import VerificationJob
from app.domain.ports.verification_job_store import VerificationJobStore


@dataclass(slots=True)
class SubmitVerificationScanUseCase:
    """Accepts a URL for asynchronous verification.

    The job is persisted as QUEUED and handed to the dispatcher; the caller gets
    an id to poll immediately, without waiting for the pipeline.
    """

    job_store: VerificationJobStore
    dispatcher: VerificationJobDispatcher
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def execute(
        self,
        owner_user_id: str,
        url: str,
        webhook_url: str | None = None,
    ) -> VerificationJob:
        job = VerificationJob.queue(
            job_id=uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            url=url,
            webhook_url=webhook_url,
            now=self.current_time_provider(),
        )
        self.job_store.save(job)
        self.dispatcher.dispatch(job.id)
        return job

    def execute_batch(
        self,
        owner_user_id: str,
        urls: list[str],
        webhook_url: str | None = None,
    ) -> list[VerificationJob]:
        return [self.execute(owner_user_id, url, webhook_url) for url in urls]
