from app.infrastructure.external_services.outbound_target_guard import SafeOutboundResolution
from app.infrastructure.external_services.pinned_http_client import (
    PinnedHttpResponse,
    send_pinned_get_request,
    send_pinned_post_request,
)


class _FakeResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.status = status
        self._headers = headers
        self._body = body

    def getheaders(self):
        return list(self._headers.items())

    def read(self, max_bytes: int | None = None) -> bytes:
        if max_bytes is None:
            return self._body
        return self._body[:max_bytes]


class _FakeConnection:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.request_args: tuple[str, str, dict[str, str]] | None = None
        self.closed = False

    def request(self, method: str, path: str, headers: dict[str, str]) -> None:
        self.request_args = (method, path, headers)

    def getresponse(self) -> _FakeResponse:
        return self._response

    def close(self) -> None:
        self.closed = True


def test_pinned_http_client_uses_validated_ip_for_actual_connection(
    monkeypatch,
) -> None:
    observed: list[tuple[str, str, int, float]] = []

    monkeypatch.setattr(
        "app.infrastructure.external_services.pinned_http_client.resolve_safe_outbound_url",
        lambda url: SafeOutboundResolution(
            hostname="example.org",
            port=443,
            ip_addresses=("203.0.113.10",),
        ),
    )

    fake_connection = _FakeConnection(
        _FakeResponse(200, {"Content-Type": "text/html; charset=utf-8"}, b"<html>ok</html>")
    )

    def fake_build_connection(*, parsed, resolution, destination_ip, timeout_seconds):
        observed.append((resolution.hostname, destination_ip, resolution.port, timeout_seconds))
        return fake_connection

    monkeypatch.setattr(
        "app.infrastructure.external_services.pinned_http_client._build_connection",
        fake_build_connection,
    )

    response = send_pinned_get_request(
        "https://example.org/login?next=/mail",
        headers={"User-Agent": "Verifiko/1.0"},
        timeout_seconds=3.0,
        read_body=True,
        max_bytes=32,
    )

    assert response == PinnedHttpResponse(
        status_code=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        body=b"<html>ok</html>",
    )
    assert observed == [("example.org", "203.0.113.10", 443, 3.0)]
    assert fake_connection.request_args == (
        "GET",
        "/login?next=/mail",
        {"User-Agent": "Verifiko/1.0"},
    )
    assert fake_connection.closed is True


class _FakePostConnection:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.request_args: tuple[str, str, bytes, dict[str, str]] | None = None
        self.getresponse_calls = 0

    def request(self, method: str, path: str, body=None, headers=None) -> None:
        self.request_args = (method, path, body, dict(headers or {}))

    def getresponse(self) -> _FakeResponse:
        self.getresponse_calls += 1
        return self._response

    def close(self) -> None:
        pass


def test_pinned_post_request_pins_ip_and_does_not_follow_redirects(monkeypatch) -> None:
    observed_destinations: list[str] = []

    monkeypatch.setattr(
        "app.infrastructure.external_services.pinned_http_client.resolve_safe_outbound_url",
        lambda url: SafeOutboundResolution(
            hostname="hooks.example",
            port=443,
            ip_addresses=("203.0.113.10",),
        ),
    )

    # A 302 pointing at an internal host: the pinned client must return it as-is,
    # never follow it (that would forward the signed headers off to the attacker's
    # Location and defeat the SSRF guard).
    fake_connection = _FakePostConnection(
        _FakeResponse(302, {"Location": "https://169.254.169.254/"}, b"")
    )

    monkeypatch.setattr(
        "app.infrastructure.external_services.pinned_http_client._build_connection",
        lambda *, parsed, resolution, destination_ip, timeout_seconds: observed_destinations.append(
            destination_ip
        )
        or fake_connection,
    )

    response = send_pinned_post_request(
        "https://hooks.example/verifiko",
        headers={"X-Verifiko-Signature": "sha256=abc"},
        body=b'{"event":"scan.completed"}',
        timeout_seconds=5.0,
    )

    assert response.status_code == 302  # returned, not followed
    assert observed_destinations == ["203.0.113.10"]
    assert fake_connection.getresponse_calls == 1  # exactly one request, no redirect hop
    assert fake_connection.request_args == (
        "POST",
        "/verifiko",
        b'{"event":"scan.completed"}',
        {"X-Verifiko-Signature": "sha256=abc"},
    )
