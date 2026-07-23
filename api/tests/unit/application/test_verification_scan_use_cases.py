import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.application.exceptions.application_exception import VerificationScanNotFoundError
from app.application.ports.verification_job_dispatcher import VerificationJobDispatcher
from app.application.services.verification_scan_processor import VerificationScanProcessor
from app.application.use_cases.get_verification_scan import GetVerificationScanUseCase
from app.application.use_cases.submit_verification_scan import SubmitVerificationScanUseCase
from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.domain.exceptions.domain_exception import DomainException
from app.infrastructure.jobs.verification_job_stores import InMemoryVerificationJobStore

_OWNER = str(uuid.uuid4())
_NOW = lambda: datetime(2026, 7, 23, tzinfo=timezone.utc)


class RecordingDispatcher(VerificationJobDispatcher):
    def __init__(self) -> None:
        self.dispatched: list[str] = []

    def dispatch(self, job_id: str) -> None:
        self.dispatched.append(job_id)


class FakeCreateUseCase:
    def __init__(self, result_id: str = "ver-1", error: Exception | None = None) -> None:
        self.result_id = result_id
        self.error = error
        self.calls: list[str] = []

    def execute(self, command):
        self.calls.append(command.url)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(id=self.result_id)


def test_submit_queues_saves_and_dispatches() -> None:
    store = InMemoryVerificationJobStore()
    dispatcher = RecordingDispatcher()
    use_case = SubmitVerificationScanUseCase(store, dispatcher, current_time_provider=_NOW)

    job = use_case.execute(owner_user_id=_OWNER, url="https://example.com")

    assert job.status is VerificationJobStatus.QUEUED
    saved = store.get(job.id)
    assert saved is not None and saved.owner_user_id == _OWNER
    assert dispatcher.dispatched == [job.id]


def test_submit_batch_creates_one_job_per_url() -> None:
    store = InMemoryVerificationJobStore()
    dispatcher = RecordingDispatcher()
    use_case = SubmitVerificationScanUseCase(store, dispatcher, current_time_provider=_NOW)

    jobs = use_case.execute_batch(_OWNER, ["https://a.example", "https://b.example"])

    assert len(jobs) == 2
    assert {j.url for j in jobs} == {"https://a.example", "https://b.example"}
    assert len(dispatcher.dispatched) == 2


def test_get_scan_is_owner_scoped() -> None:
    store = InMemoryVerificationJobStore()
    dispatcher = RecordingDispatcher()
    submit = SubmitVerificationScanUseCase(store, dispatcher, current_time_provider=_NOW)
    job = submit.execute(_OWNER, "https://example.com")

    get = GetVerificationScanUseCase(store)

    assert get.execute(job.id, _OWNER).id == job.id
    with pytest.raises(VerificationScanNotFoundError):
        get.execute(job.id, str(uuid.uuid4()))
    with pytest.raises(VerificationScanNotFoundError):
        get.execute("missing", _OWNER)


def _queued_job(store: InMemoryVerificationJobStore) -> VerificationJob:
    job = VerificationJob.queue(
        job_id="scan-1", owner_user_id=_OWNER, url="https://example.com", now=_NOW()
    )
    store.save(job)
    return job


def test_processor_completes_job_with_result_id() -> None:
    store = InMemoryVerificationJobStore()
    _queued_job(store)
    processor = VerificationScanProcessor(
        job_store=store,
        create_use_case=FakeCreateUseCase(result_id="ver-99"),
        current_time_provider=_NOW,
    )

    processor.process("scan-1")

    done = store.get("scan-1")
    assert done is not None
    assert done.status is VerificationJobStatus.COMPLETED
    assert done.result_verification_id == "ver-99"


def test_processor_marks_failed_on_domain_exception() -> None:
    store = InMemoryVerificationJobStore()
    _queued_job(store)
    processor = VerificationScanProcessor(
        job_store=store,
        create_use_case=FakeCreateUseCase(error=DomainException("Only HTTP and HTTPS URLs are supported.")),
        current_time_provider=_NOW,
    )

    processor.process("scan-1")

    done = store.get("scan-1")
    assert done is not None
    assert done.status is VerificationJobStatus.FAILED
    assert "HTTP" in (done.error_message or "")


def test_processor_marks_failed_on_unexpected_error_without_leaking() -> None:
    store = InMemoryVerificationJobStore()
    _queued_job(store)
    processor = VerificationScanProcessor(
        job_store=store,
        create_use_case=FakeCreateUseCase(error=RuntimeError("boom secret")),
        current_time_provider=_NOW,
    )

    processor.process("scan-1")

    done = store.get("scan-1")
    assert done is not None
    assert done.status is VerificationJobStatus.FAILED
    assert "boom secret" not in (done.error_message or "")


def test_processor_skips_terminal_job() -> None:
    store = InMemoryVerificationJobStore()
    job = _queued_job(store)
    job.mark_completed("ver-1", now=_NOW())
    store.save(job)
    fake = FakeCreateUseCase()
    processor = VerificationScanProcessor(store, fake, current_time_provider=_NOW)

    processor.process("scan-1")

    assert fake.calls == []  # not re-processed
