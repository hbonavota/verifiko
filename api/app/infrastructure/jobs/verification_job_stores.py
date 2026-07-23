from __future__ import annotations

import json
import threading
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.domain.ports.verification_job_store import VerificationJobStore


class InMemoryVerificationJobStore(VerificationJobStore):
    """Process-local job store. Suitable for single-replica deployments and
    tests; use the Redis store when job state must be shared or survive across
    replicas."""

    def __init__(self) -> None:
        self._jobs: dict[str, VerificationJob] = {}
        self._lock = threading.Lock()

    def save(self, job: VerificationJob) -> None:
        with self._lock:
            # Store a copy so later in-place mutations by a worker are not
            # observed until an explicit save.
            self._jobs[job.id] = replace(job)

    def get(self, job_id: str) -> VerificationJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return replace(job) if job is not None else None

    def get_for_owner(self, job_id: str, owner_user_id: str) -> VerificationJob | None:
        job = self.get(job_id)
        if job is None or job.owner_user_id != owner_user_id:
            return None
        return job


class RedisVerificationJobStore(VerificationJobStore):
    """Redis-backed job store so scan state is shared across replicas and
    expires automatically."""

    def __init__(self, redis_client: Any, key_prefix: str, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds

    def save(self, job: VerificationJob) -> None:
        self._redis.setex(self._key(job.id), self._ttl_seconds, json.dumps(_encode(job)))

    def get(self, job_id: str) -> VerificationJob | None:
        raw = self._redis.get(self._key(job_id))
        if raw is None:
            return None
        return _decode(json.loads(raw))

    def get_for_owner(self, job_id: str, owner_user_id: str) -> VerificationJob | None:
        job = self.get(job_id)
        if job is None or job.owner_user_id != owner_user_id:
            return None
        return job

    def _key(self, job_id: str) -> str:
        return f"{self._key_prefix}:{job_id}"


def _encode(job: VerificationJob) -> dict:
    return {
        "id": job.id,
        "owner_user_id": job.owner_user_id,
        "url": job.url,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "result_verification_id": job.result_verification_id,
        "error_message": job.error_message,
    }


def _decode(payload: dict) -> VerificationJob:
    return VerificationJob(
        id=payload["id"],
        owner_user_id=payload["owner_user_id"],
        url=payload["url"],
        status=VerificationJobStatus(payload["status"]),
        created_at=_parse_dt(payload["created_at"]),
        updated_at=_parse_dt(payload["updated_at"]),
        result_verification_id=payload.get("result_verification_id"),
        error_message=payload.get("error_message"),
    )


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
