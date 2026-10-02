import http.client
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from app.infrastructure.external_services.outbound_target_guard import (
    SafeOutboundResolution,
    resolve_safe_outbound_url,
)


@dataclass(frozen=True, slots=True)
class PinnedHttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        destination_ip: str,
        timeout: float,
    ) -> None:
        super().__init__(host=host, port=port, timeout=timeout)
        self._destination_ip = destination_ip

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._destination_ip, self.port),
            timeout=self.timeout,
            source_address=self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        destination_ip: str,
        timeout: float,
        context: ssl.SSLContext | None = None,
    ) -> None:
        super().__init__(host=host, port=port, timeout=timeout, context=context)
        self._destination_ip = destination_ip

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._destination_ip, self.port),
            timeout=self.timeout,
            source_address=self.source_address,
        )
        if self._tunnel_host:
            self.sock = raw_socket
            self._tunnel()
        self.sock = self._context.wrap_socket(
            raw_socket,
            server_hostname=self.host,
        )


def send_pinned_get_request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: float,
    read_body: bool,
    max_bytes: int | None = None,
) -> PinnedHttpResponse:
    return _send_pinned_request(
        url,
        method="GET",
        headers=headers,
        body=None,
        timeout_seconds=timeout_seconds,
        read_body=read_body,
        max_bytes=max_bytes,
    )


def send_pinned_post_request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
    timeout_seconds: float,
    read_body: bool = False,
    max_bytes: int | None = None,
) -> PinnedHttpResponse:
    """POST to a URL over a connection pinned to a guard-validated IP.

    Like the GET variant, the hostname is resolved and validated once, the socket
    connects only to those addresses, and ``http.client`` is used directly — so
    it never re-resolves DNS (no rebinding window) and never follows redirects (a
    3xx is returned as-is). This is what makes outbound POSTs to user-controlled
    destinations, such as scan webhooks, safe against SSRF.
    """
    return _send_pinned_request(
        url,
        method="POST",
        headers=headers,
        body=body,
        timeout_seconds=timeout_seconds,
        read_body=read_body,
        max_bytes=max_bytes,
    )


def _send_pinned_request(
    url: str,
    *,
    method: str,
    headers: dict[str, str] | None,
    body: bytes | None,
    timeout_seconds: float,
    read_body: bool,
    max_bytes: int | None,
) -> PinnedHttpResponse:
    parsed = urlsplit(url)
    resolution = resolve_safe_outbound_url(url)
    request_headers = dict(headers or {})
    path = _request_path(parsed)
    last_error: Exception | None = None

    for ip_address in resolution.ip_addresses:
        connection = _build_connection(
            parsed=parsed,
            resolution=resolution,
            destination_ip=ip_address,
            timeout_seconds=timeout_seconds,
        )
        try:
            if body is None:
                connection.request(method, path, headers=request_headers)
            else:
                connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            response_body = response.read(max_bytes) if read_body else b""
            return PinnedHttpResponse(
                status_code=response.status,
                headers={key: value for key, value in response.getheaders()},
                body=response_body,
            )
        except (http.client.HTTPException, socket.timeout, OSError, ssl.SSLError) as exc:
            last_error = exc
        finally:
            connection.close()

    if last_error is not None:
        raise last_error
    raise OSError("No validated outbound address could be reached.")


def _build_connection(
    *,
    parsed: SplitResult,
    resolution: SafeOutboundResolution,
    destination_ip: str,
    timeout_seconds: float,
):
    if parsed.scheme == "https":
        return _PinnedHTTPSConnection(
            host=resolution.hostname,
            port=resolution.port,
            destination_ip=destination_ip,
            timeout=timeout_seconds,
            context=ssl.create_default_context(),
        )
    return _PinnedHTTPConnection(
        host=resolution.hostname,
        port=resolution.port,
        destination_ip=destination_ip,
        timeout=timeout_seconds,
    )


def _request_path(parsed: SplitResult) -> str:
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path
