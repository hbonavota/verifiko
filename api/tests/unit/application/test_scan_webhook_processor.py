import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.application.ports.scan_webhook_notifier import ScanWebhookNotifierPort
from app.application.ports.verification_job_dispatcher import VerificationJobDispatcher
from app.application.services.verification_scan_processor import VerificationScanProcessor
from app.application.use_cases.submit_verification_scan import SubmitVerificationScanUseCase
from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.infrastructure.jobs.verification_job_stores import InMemoryVerificationJobStore

_OWNER = str(uuid.uuid4())
_NOW = lambda: datetime(2026, 7, 23, tzinfo=timezone.utc)


class RecordingNotifier(ScanWebhookNotifierPort):
    def __init__(self) -> None:
        self.notified: list[VerificationJob] = []

    def notify(self, job: VerificationJob) -> None:
        self.notified.append(job)


class FakeCreateUseCase:
    def execute(self, command):
        return SimpleNamespace(id="ver-1", screenshot_ref=None)


class NoDispatch(VerificationJobDispatcher):
    def dispatch(self, job_id: str) -> None:  # not exercised here
        pass


def _queue(store, *, webhook_url):
    job = VerificationJob.queue(
        job_id="scan-1",
        owner_user_id=_OWNER,
        url="https://example.com",
        webhook_url=webhook_url,
        now=_NOW(),
    )
    store.save(job)
    return job


def test_processor_notifies_when_webhook_url_present() -> None:
    store = InMemoryVerificationJobStore()
    _queue(store, webhook_url="https://hooks.example/cb")
    notifier = RecordingNotifier()
    processor = VerificationScanProcessor(
        job_store=store,
        create_use_case=FakeCreateUseCase(),
        webhook_notifier=notifier,
        current_time_provider=_NOW,
    )

    processor.process("scan-1")

    assert len(notifier.notified) == 1
    delivered = notifier.notified[0]
    assert delivered.status is VerificationJobStatus.COMPLETED
    assert delivered.webhook_url == "https://hooks.example/cb"


def test_processor_does_not_notify_without_webhook_url() -> None:
    store = InMemoryVerificationJobStore()
    _queue(store, webhook_url=None)
    notifier = RecordingNotifier()
    processor = VerificationScanProcessor(
        job_store=store,
        create_use_case=FakeCreateUseCase(),
        webhook_notifier=notifier,
        current_time_provider=_NOW,
    )

    processor.process("scan-1")

    assert notifier.notified == []


def test_submit_persists_webhook_url_on_job() -> None:
    store = InMemoryVerificationJobStore()
    submit = SubmitVerificationScanUseCase(store, NoDispatch(), current_time_provider=_NOW)

    job = submit.execute(_OWNER, "https://example.com", webhook_url="https://hooks.example/cb")

    saved = store.get(job.id)
    assert saved is not None
    assert saved.webhook_url == "https://hooks.example/cb"


def test_submit_batch_applies_webhook_url_to_all() -> None:
    store = InMemoryVerificationJobStore()
    submit = SubmitVerificationScanUseCase(store, NoDispatch(), current_time_provider=_NOW)

    jobs = submit.execute_batch(
        _OWNER, ["https://a.example", "https://b.example"], webhook_url="https://hooks.example/cb"
    )

    assert all(store.get(j.id).webhook_url == "https://hooks.example/cb" for j in jobs)
