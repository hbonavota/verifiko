import json

from app.infrastructure.jobs.scan_dispatchers import (
    QStashDeliveryError,
    QStashVerificationJobDispatcher,
)


class _RecordingPoster:
    def __init__(self, status_code: int = 200, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        self.calls: list[tuple[str, dict[str, str], bytes]] = []

    def __call__(self, url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        self.calls.append((url, headers, body))
        return self.status_code, self.body


def _dispatcher(poster) -> QStashVerificationJobDispatcher:
    return QStashVerificationJobDispatcher(
        token="qstash-token",
        publish_base_url="https://qstash.upstash.io/v2/publish/",
        callback_url="https://api.verifiko.es/api/v1/scans/process",
        http_poster=poster,
        max_retries=3,
    )


def test_dispatch_publishes_to_qstash_with_destination_and_auth() -> None:
    poster = _RecordingPoster()
    _dispatcher(poster).dispatch("job-42")

    assert len(poster.calls) == 1
    url, headers, body = poster.calls[0]
    assert url == (
        "https://qstash.upstash.io/v2/publish/"
        "https://api.verifiko.es/api/v1/scans/process"
    )
    assert headers["Authorization"] == "Bearer qstash-token"
    assert headers["Content-Type"] == "application/json"
    assert headers["Upstash-Retries"] == "3"
    assert json.loads(body) == {"job_id": "job-42"}


def test_dispatch_swallows_transport_error() -> None:
    def _raising(url, headers, body):
        raise QStashDeliveryError("boom")

    # A publish failure must not bubble up into the user's submit request.
    _dispatcher(_raising).dispatch("job-99")


def test_dispatch_swallows_non_2xx_response() -> None:
    poster = _RecordingPoster(status_code=500, body="server error")
    _dispatcher(poster).dispatch("job-7")

    assert len(poster.calls) == 1
