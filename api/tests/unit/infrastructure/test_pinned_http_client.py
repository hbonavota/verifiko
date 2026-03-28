from app.infrastructure.external_services.outbound_target_guard import SafeOutboundResolution
from app.infrastructure.external_services.pinned_http_client import (
    PinnedHttpResponse,
    send_pinned_get_request,
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
