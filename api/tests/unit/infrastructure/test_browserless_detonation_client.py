import json

import pytest

from app.application.ports.headless_detonation import HeadlessDetonationError
from app.infrastructure.detonation.browserless_detonation_client import (
    BrowserlessDetonationClient,
    NullHeadlessDetonation,
)


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
