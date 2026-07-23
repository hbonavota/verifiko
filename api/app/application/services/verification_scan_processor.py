from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.domain.exceptions.domain_exception import DomainException
from app.domain.ports.verification_job_store import VerificationJobStore
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class VerificationScanProcessor:
    """Runs a queued scan through the existing synchronous verification pipeline
    and records the outcome on its job.

    This is what a worker (in-process today, a distributed consumer tomorrow)
    invokes. It reuses ``CreateURLVerificationUseCase`` unchanged, so async and
    sync verification share exactly the same detection logic.
    """

    job_store: VerificationJobStore
    create_use_case: CreateURLVerificationUseCase
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def process(self, job_id: str) -> None:
        job = self.job_store.get(job_id)
        if job is None or job.is_terminal:
            return

        job.mark_running(self.current_time_provider())
        self.job_store.save(job)

        try:
            dto = self.create_use_case.execute(
                CreateVerificationCommand(
                    url=job.url,
                    user_id=UserId.from_string(job.owner_user_id),
                )
            )
        except DomainException as exc:
            job.mark_failed(str(exc), self.current_time_provider())
            self.job_store.save(job)
            return
        except Exception:
            job.mark_failed(
                "Verification could not be completed due to an internal error.",
                self.current_time_provider(),
            )
            self.job_store.save(job)
            return

        job.mark_completed(dto.id, self.current_time_provider())
        self.job_store.save(job)
