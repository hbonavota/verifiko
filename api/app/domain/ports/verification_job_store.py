from abc import ABC, abstractmethod

from app.domain.entities.verification_job import VerificationJob


class VerificationJobStore(ABC):
    @abstractmethod
    def save(self, job: VerificationJob) -> None:
        """Insert or update a job."""
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: str) -> VerificationJob | None:
        """Fetch a job regardless of owner (for the worker)."""
        raise NotImplementedError

    @abstractmethod
    def get_for_owner(self, job_id: str, owner_user_id: str) -> VerificationJob | None:
        """Fetch a job only if it belongs to ``owner_user_id`` (for the API)."""
        raise NotImplementedError

    def screenshot_ref_for_result(
        self, result_verification_id: str, owner_user_id: str
    ) -> str | None:
        """Return the detonation screenshot reference for the scan job that
        produced ``result_verification_id`` (owner-scoped), or ``None``.

        A concrete no-op default keeps stores that never capture screenshots
        (e.g. the in-memory test store) working without change.
        """
        return None
