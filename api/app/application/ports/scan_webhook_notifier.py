from abc import ABC, abstractmethod

from app.domain.entities.verification_job import VerificationJob


class ScanWebhookNotifierPort(ABC):
    @abstractmethod
    def notify(self, job: VerificationJob) -> None:
        """Deliver a terminal-state notification for a scan, best-effort.

        Implementations must never raise back to the worker: a failed delivery
        is logged, not propagated (the poll endpoint remains the source of
        truth).
        """
        raise NotImplementedError
