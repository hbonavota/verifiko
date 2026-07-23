from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from app.application.ports.verification_job_dispatcher import VerificationJobDispatcher
from app.application.services.verification_scan_processor import VerificationScanProcessor

logger = logging.getLogger(__name__)


class SynchronousVerificationJobDispatcher(VerificationJobDispatcher):
    """Processes the job inline. Used in tests and simple deployments where
    async semantics are not required."""

    def __init__(self, processor: VerificationScanProcessor) -> None:
        self._processor = processor

    def dispatch(self, job_id: str) -> None:
        self._processor.process(job_id)


class ThreadPoolVerificationJobDispatcher(VerificationJobDispatcher):
    """Runs the verification pipeline on a background thread pool so the request
    thread returns immediately with a 202.

    This is the in-process worker. The dispatcher is a port, so swapping this for
    a durable distributed queue (e.g. Redis Streams with a separate consumer)
    later requires no change to the API or use cases.
    """

    def __init__(self, processor: VerificationScanProcessor, max_workers: int = 4) -> None:
        self._processor = processor
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="verifiko-scan"
        )

    def dispatch(self, job_id: str) -> None:
        future = self._executor.submit(self._processor.process, job_id)
        future.add_done_callback(lambda done: self._log_failure(job_id, done))

    @staticmethod
    def _log_failure(job_id: str, future) -> None:
        exception = future.exception()
        if exception is not None:  # pragma: no cover - defensive; processor handles its own errors
            logger.exception("Scan job %s crashed in the worker", job_id, exc_info=exception)
