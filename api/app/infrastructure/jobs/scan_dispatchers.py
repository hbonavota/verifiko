from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.application.ports.verification_job_dispatcher import VerificationJobDispatcher
from app.application.services.verification_scan_processor import VerificationScanProcessor

logger = logging.getLogger(__name__)

# A poster returns (status_code, body) and raises on transport-level failure so
# the dispatcher can log a delivery problem without crashing the request.
QStashHttpPoster = Callable[[str, dict[str, str], bytes], tuple[int, str]]


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


class QStashDeliveryError(Exception):
    """Raised by the default poster on a transport-level failure."""


class QStashVerificationJobDispatcher(VerificationJobDispatcher):
    """Hands the job to Upstash QStash, which then invokes the internal worker
    endpoint as its own HTTP request.

    On serverless (Vercel) a background thread is not guaranteed to keep running
    once the 202 response is sent, so a 10-30s detonation can be frozen midway.
    Publishing to QStash instead makes the pipeline run in a *separate*
    invocation (the internal ``/scans/process`` endpoint), with QStash providing
    at-least-once delivery and retries. The dispatcher is a port, so the API and
    use cases are unchanged.

    Publishing is best-effort from the request's point of view: a publish failure
    is logged and the job stays QUEUED rather than failing the user's submit. It
    never blocks on the pipeline itself.
    """

    def __init__(
        self,
        *,
        token: str,
        publish_base_url: str,
        callback_url: str,
        http_poster: QStashHttpPoster,
        max_retries: int = 3,
    ) -> None:
        self._token = token
        # QStash publishes to ``{publish_base_url}{destination_url}``.
        self._publish_url = publish_base_url.rstrip("/") + "/" + callback_url
        self._max_retries = max_retries
        self._http_poster = http_poster

    def dispatch(self, job_id: str) -> None:
        body = json.dumps({"job_id": job_id}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            # QStash forwards this body to the destination and retries on a
            # non-2xx response from the worker.
            "Upstash-Retries": str(self._max_retries),
        }
        try:
            status_code, response_body = self._http_poster(self._publish_url, headers, body)
        except QStashDeliveryError:
            logger.exception(
                "Failed to publish scan job %s to QStash; it remains queued.", job_id
            )
            return
        if not 200 <= status_code < 300:
            logger.error(
                "QStash rejected publish for scan job %s: status=%s body=%s",
                job_id,
                status_code,
                response_body[:200],
            )


def build_urllib_qstash_poster(timeout_seconds: float = 5.0) -> QStashHttpPoster:
    """A poster backed by urllib. Network errors surface as
    ``QStashDeliveryError`` so the dispatcher can log a delivery problem."""

    def _post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                detail = ""
            return exc.code, detail
        except (URLError, TimeoutError, OSError) as exc:
            raise QStashDeliveryError(str(exc)) from exc

    return _post
