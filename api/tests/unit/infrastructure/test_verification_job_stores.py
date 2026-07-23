from datetime import datetime, timezone

from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.infrastructure.jobs.verification_job_stores import (
    InMemoryVerificationJobStore,
    RedisVerificationJobStore,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str):
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl


def _job(job_id: str = "scan-1", owner: str = "owner-1") -> VerificationJob:
    return VerificationJob.queue(
        job_id=job_id,
        owner_user_id=owner,
        url="https://example.com",
        now=datetime(2026, 7, 23, tzinfo=timezone.utc),
    )


def test_in_memory_save_and_get() -> None:
    store = InMemoryVerificationJobStore()
    store.save(_job())

    fetched = store.get("scan-1")
    assert fetched is not None
    assert fetched.status is VerificationJobStatus.QUEUED


def test_in_memory_is_owner_scoped() -> None:
    store = InMemoryVerificationJobStore()
    store.save(_job(owner="owner-1"))

    assert store.get_for_owner("scan-1", "owner-1") is not None
    assert store.get_for_owner("scan-1", "someone-else") is None


def test_in_memory_returns_snapshot_not_live_reference() -> None:
    store = InMemoryVerificationJobStore()
    job = _job()
    store.save(job)

    job.mark_completed("ver-1")  # mutate after saving

    fetched = store.get("scan-1")
    assert fetched is not None
    assert fetched.status is VerificationJobStatus.QUEUED  # unaffected


def test_redis_round_trips_all_fields() -> None:
    redis = FakeRedis()
    store = RedisVerificationJobStore(redis, key_prefix="verifiko:scan", ttl_seconds=99)
    job = _job()
    job.mark_completed("ver-42", now=datetime(2026, 7, 23, 1, tzinfo=timezone.utc))
    store.save(job)

    assert redis.ttls["verifiko:scan:scan-1"] == 99
    fetched = store.get("scan-1")
    assert fetched is not None
    assert fetched.status is VerificationJobStatus.COMPLETED
    assert fetched.result_verification_id == "ver-42"
    assert fetched.owner_user_id == "owner-1"


def test_redis_owner_scoping_and_missing() -> None:
    store = RedisVerificationJobStore(FakeRedis(), key_prefix="verifiko:scan", ttl_seconds=99)
    store.save(_job(owner="owner-1"))

    assert store.get_for_owner("scan-1", "owner-1") is not None
    assert store.get_for_owner("scan-1", "other") is None
    assert store.get("missing") is None


def test_redis_round_trips_webhook_url() -> None:
    store = RedisVerificationJobStore(FakeRedis(), key_prefix="verifiko:scan", ttl_seconds=99)
    job = VerificationJob.queue(
        job_id="scan-1",
        owner_user_id="owner-1",
        url="https://example.com",
        webhook_url="https://hooks.example/cb",
        now=datetime(2026, 7, 23, tzinfo=timezone.utc),
    )
    store.save(job)

    fetched = store.get("scan-1")
    assert fetched is not None
    assert fetched.webhook_url == "https://hooks.example/cb"
