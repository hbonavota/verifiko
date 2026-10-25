from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.infrastructure.persistence.models.base_model import VerificationJobModel
from app.infrastructure.persistence.repositories.sqlalchemy_verification_job_store import (
    SqlAlchemyVerificationJobStore,
)


def _store() -> SqlAlchemyVerificationJobStore:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    VerificationJobModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return SqlAlchemyVerificationJobStore(factory)


def _queued_job(owner: str = "user-1") -> VerificationJob:
    return VerificationJob.queue(
        job_id="job-1",
        owner_user_id=owner,
        url="https://example.org/login",
        webhook_url="https://hooks.example/verifiko",
        now=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
    )


def test_save_then_get_roundtrips_all_fields() -> None:
    store = _store()
    job = _queued_job()
    store.save(job)

    loaded = store.get("job-1")
    assert loaded is not None
    assert loaded.owner_user_id == "user-1"
    assert loaded.url == "https://example.org/login"
    assert loaded.status is VerificationJobStatus.QUEUED
    assert loaded.webhook_url == "https://hooks.example/verifiko"
    assert loaded.created_at.tzinfo is not None


def test_save_upserts_lifecycle_transitions() -> None:
    store = _store()
    job = _queued_job()
    store.save(job)

    job.mark_running()
    store.save(job)
    job.mark_completed("verification-42")
    store.save(job)

    loaded = store.get("job-1")
    assert loaded is not None
    assert loaded.status is VerificationJobStatus.COMPLETED
    assert loaded.result_verification_id == "verification-42"
    assert loaded.error_message is None


def test_get_for_owner_scopes_by_owner() -> None:
    store = _store()
    store.save(_queued_job(owner="user-1"))

    assert store.get_for_owner("job-1", "user-1") is not None
    assert store.get_for_owner("job-1", "someone-else") is None


def test_get_unknown_job_returns_none() -> None:
    store = _store()
    assert store.get("missing") is None
    assert store.get_for_owner("missing", "user-1") is None


def test_screenshot_ref_for_result_is_owner_and_result_scoped() -> None:
    store = _store()
    job = _queued_job(owner="user-1")
    job.screenshot_ref = "screenshots/abc.png"
    job.mark_completed("verification-42")
    store.save(job)

    assert (
        store.screenshot_ref_for_result("verification-42", "user-1")
        == "screenshots/abc.png"
    )
    # Never leaks across owners or to the wrong verification.
    assert store.screenshot_ref_for_result("verification-42", "someone-else") is None
    assert store.screenshot_ref_for_result("other-verification", "user-1") is None
