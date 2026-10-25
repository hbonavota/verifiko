import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.commands.create_verification_command import (
    CreateVerificationCommand,
)
from app.application.ports.scan_webhook_notifier import ScanWebhookNotifierPort
from app.application.use_cases.create_url_verification import (
    CreateURLVerificationUseCase,
)
from app.domain.exceptions.domain_exception import DomainException
from app.domain.ports.verification_job_store import VerificationJobStore
from app.domain.value_objects.user_id import UserId

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VerificationScanProcessor:
    """Runs a queued scan through the existing synchronous verification pipeline
    and records the outcome on its job.

    This is what a worker (in-process today, a distributed consumer tomorrow)
    invokes. It reuses ``CreateURLVerificationUseCase`` unchanged, so async and
    sync verification share exactly the same detection logic. Once the job
    reaches a terminal state, an optional webhook is delivered best-effort.
    """

    job_store: VerificationJobStore
    create_use_case: CreateURLVerificationUseCase
    webhook_notifier: ScanWebhookNotifierPort | None = None
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(UTC)

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
                    # Async scans opt into dynamic analysis; the use case still
                    # gates the actual browser run behind DetonationPolicy and the
                    # DETONATION_ENABLED flag.
                    deep_analysis=True,
                )
            )
        except DomainException as exc:
            job.mark_failed(str(exc), self.current_time_provider())
        except Exception:
            job.mark_failed(
                "Verification could not be completed due to an internal error.",
                self.current_time_provider(),
            )
        else:
            # A screenshot is a scan-scoped artifact: carry the detonation's
            # opaque reference onto the job so the result route can mint a
            # presigned URL for it later.
            job.screenshot_ref = dto.screenshot_ref
            job.mark_completed(dto.id, self.current_time_provider())

        self.job_store.save(job)
        self._deliver_webhook(job)

    def _deliver_webhook(self, job) -> None:
        if self.webhook_notifier is None or not job.webhook_url:
            return
        try:
            self.webhook_notifier.notify(job)
        except Exception:  # pragma: no cover - notifier is already best-effort
            logger.exception("Webhook notification failed for scan %s", job.id)
