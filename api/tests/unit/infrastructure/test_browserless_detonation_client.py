import base64
import json

import pytest

from app.application.ports.headless_detonation import HeadlessDetonationError
from app.application.ports.screenshot_store import (
    ScreenshotStoreError,
    ScreenshotStorePort,
)
from app.infrastructure.detonation.browserless_detonation_client import (
    BrowserlessDetonationClient,
    NullHeadlessDetonation,
)
from app.infrastructure.storage.screenshot_store import NullScreenshotStore


class _RecordingStore(ScreenshotStorePort):
    def __init__(self, ref: str = "screenshots/fake.png", error: Exception | None = None) -> None:
        self.ref = ref
        self.error = error
        self.stored: list[bytes] = []

    def store(self, image_bytes: bytes, *, content_type: str = "image/png") -> str:
        self.stored.append(image_bytes)
        if self.error is not None:
            raise self.error
        return self.ref

    def presigned_url(self, ref: str, *, expires_in: int = 3600) -> str:
        return f"https://signed.example/{ref}"


_PNG_BYTES = b"\x89PNG\r\n\x1a\n fake image"
_PNG_B64 = base64.b64encode(_PNG_BYTES).decode("ascii")


class _RecordingPoster:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = body
        self.calls: list[dict] = []

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return self.status, self.body


def _result_body(**overrides) -> str:
    data = {
        "requested_url": "https://scan.example/login",
        "final_url": "https://scan.example/login",
        "page_title": "Sign in",
        "forms": [{"has_password_field": True, "action_host": "collector.evil.net"}],
        "third_party_hosts": ["cdn.example", "collector.evil.net"],
        "downloads": [],
        "timed_out": False,
    }
    data.update(overrides)
    return json.dumps({"data": data, "type": "application/json"})


def test_parses_browserless_response_into_detonation_result() -> None:
    poster = _RecordingPoster(200, _result_body())
    client = BrowserlessDetonationClient(endpoint="https://bl.test/function?token=x", http_poster=poster)

    result = client.detonate("https://scan.example/login")

    assert result.final_url == "https://scan.example/login"
    assert result.page_title == "Sign in"
    assert len(result.forms) == 1
    assert result.forms[0].has_password_field is True
    assert result.forms[0].action_host == "collector.evil.net"
    assert "collector.evil.net" in result.third_party_hosts
    # The request carried the detonation code and the target URL as context.
    sent = json.loads(poster.calls[0]["body"])
    assert sent["context"]["url"] == "https://scan.example/login"
    assert "code" in sent


def test_request_does_not_send_accept_application_json() -> None:
    # Browserless's Cloudflare edge 404s a POST to /function that carries
    # `Accept: application/json`; the client must send `*/*` instead.
    poster = _RecordingPoster(200, _result_body())
    client = BrowserlessDetonationClient(endpoint="https://bl.test/function?token=x", http_poster=poster)

    client.detonate("https://scan.example/login")

    headers = poster.calls[0]["headers"]
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "*/*"


def test_accepts_unwrapped_result_object() -> None:
    # Some deployments return the object directly, without a "data" envelope.
    raw = json.loads(_result_body())["data"]
    poster = _RecordingPoster(200, json.dumps(raw))
    client = BrowserlessDetonationClient(endpoint="https://bl.test/function", http_poster=poster)

    result = client.detonate("https://scan.example/login")
    assert result.forms[0].action_host == "collector.evil.net"


def test_non_2xx_raises_detonation_error() -> None:
    poster = _RecordingPoster(429, "rate limited")
    client = BrowserlessDetonationClient(endpoint="https://bl.test/function", http_poster=poster)

    with pytest.raises(HeadlessDetonationError):
        client.detonate("https://scan.example/login")


def test_non_json_body_raises_detonation_error() -> None:
    poster = _RecordingPoster(200, "<html>not json</html>")
    client = BrowserlessDetonationClient(endpoint="https://bl.test/function", http_poster=poster)

    with pytest.raises(HeadlessDetonationError):
        client.detonate("https://scan.example/login")


def test_null_detonation_is_benign() -> None:
    result = NullHeadlessDetonation().detonate("https://example.com/")
    assert result.final_url == "https://example.com/"
    assert result.forms == ()
    assert result.downloads == ()


def test_screenshot_is_uploaded_and_ref_is_set() -> None:
    store = _RecordingStore(ref="screenshots/abc.png")
    poster = _RecordingPoster(200, _result_body(screenshot_base64=_PNG_B64))
    client = BrowserlessDetonationClient(
        endpoint="https://bl.test/function",
        http_poster=poster,
        screenshot_store=store,
    )

    result = client.detonate("https://scan.example/login")

    assert result.screenshot_ref == "screenshots/abc.png"
    # The decoded bytes are what got uploaded, not the base64 text.
    assert store.stored == [_PNG_BYTES]


def test_null_store_leaves_screenshot_ref_none() -> None:
    poster = _RecordingPoster(200, _result_body(screenshot_base64=_PNG_B64))
    client = BrowserlessDetonationClient(
        endpoint="https://bl.test/function",
        http_poster=poster,
        screenshot_store=NullScreenshotStore(),
    )

    result = client.detonate("https://scan.example/login")

    assert result.screenshot_ref is None


def test_default_store_is_null_and_ref_stays_none() -> None:
    poster = _RecordingPoster(200, _result_body(screenshot_base64=_PNG_B64))
    client = BrowserlessDetonationClient(
        endpoint="https://bl.test/function", http_poster=poster
    )

    assert client.detonate("https://scan.example/login").screenshot_ref is None


def test_store_failure_does_not_break_detonation() -> None:
    store = _RecordingStore(error=ScreenshotStoreError("r2 down"))
    poster = _RecordingPoster(200, _result_body(screenshot_base64=_PNG_B64))
    client = BrowserlessDetonationClient(
        endpoint="https://bl.test/function",
        http_poster=poster,
        screenshot_store=store,
    )

    result = client.detonate("https://scan.example/login")

    # Detonation still succeeds with its behavioral observations intact.
    assert result.screenshot_ref is None
    assert result.forms[0].action_host == "collector.evil.net"


def test_no_screenshot_in_response_leaves_ref_none() -> None:
    store = _RecordingStore()
    poster = _RecordingPoster(200, _result_body())  # no screenshot_base64
    client = BrowserlessDetonationClient(
        endpoint="https://bl.test/function",
        http_poster=poster,
        screenshot_store=store,
    )

    result = client.detonate("https://scan.example/login")

    assert result.screenshot_ref is None
    assert store.stored == []
