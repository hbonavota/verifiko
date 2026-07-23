from abc import ABC, abstractmethod


class VerificationJobDispatcher(ABC):
    @abstractmethod
    def dispatch(self, job_id: str) -> None:
        """Schedule processing of a queued job off the request path."""
        raise NotImplementedError
