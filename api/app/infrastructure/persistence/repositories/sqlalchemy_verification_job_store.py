from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domain.entities.verification_job import VerificationJob
from app.domain.enums.verification_job_status import VerificationJobStatus
from app.domain.ports.verification_job_store import VerificationJobStore
from app.infrastructure.persistence.models.base_model import VerificationJobModel


class SqlAlchemyVerificationJobStore(VerificationJobStore):
    """Durable, shared scan-job store backed by the primary database.

    Using Postgres (or any shared DB) instead of Redis means job state written by
    the request that accepts a scan can be read by the background worker and by
    later polling requests — even on serverless, where each is a separate
    process — without consuming the Redis command quota. ``save`` upserts by
    primary key so the queue -> running -> completed lifecycle is a sequence of
    idempotent writes.
    """

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def save(self, job: VerificationJob) -> None:
        with self._session_factory() as session:
            session.merge(_to_model(job))
            session.commit()

    def get(self, job_id: str) -> VerificationJob | None:
        with self._session_factory() as session:
            model = session.execute(
                select(VerificationJobModel).where(VerificationJobModel.id == job_id)
            ).scalar_one_or_none()
            return _to_entity(model) if model is not None else None

    def get_for_owner(self, job_id: str, owner_user_id: str) -> VerificationJob | None:
        job = self.get(job_id)
        if job is None or job.owner_user_id != owner_user_id:
            return None
        return job


def _to_model(job: VerificationJob) -> VerificationJobModel:
    return VerificationJobModel(
        id=job.id,
        owner_user_id=job.owner_user_id,
        url=job.url,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result_verification_id=job.result_verification_id,
        error_message=job.error_message,
        webhook_url=job.webhook_url,
    )


def _to_entity(model: VerificationJobModel) -> VerificationJob:
    return VerificationJob(
        id=model.id,
        owner_user_id=model.owner_user_id,
        url=model.url,
        status=VerificationJobStatus(model.status),
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
        result_verification_id=model.result_verification_id,
        error_message=model.error_message,
        webhook_url=model.webhook_url,
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
