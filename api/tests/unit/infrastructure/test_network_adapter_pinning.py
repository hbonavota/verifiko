
import pytest

from app.application.ports.redirect_resolver import RedirectResolutionError
from app.infrastructure.external_services.dns.socket_infrastructure_lookup import (
    SocketInfrastructureLookup,
)
from app.infrastructure.external_services.html.simple_html_fetcher import (
    SimpleHtmlFetcher,
)
from app.infrastructure.external_services.outbound_target_guard import (
    SafeOutboundResolution,
    UnsafeOutboundTargetError,
)
from app.infrastructure.external_services.redirects.http_redirect_resolver import (
    HttpRedirectResolver,
)
from app.infrastructure.external_services.tls.tls_client import SocketTlsValidator


def test_html_fetcher_keeps_normal_external_targets_working(monkeypatch) -> None:
    observed_headers: list[dict[str, str]] = []

    monkeypatch.setattr(
        "app.infrastructure.external_services.html.simple_html_fetcher.send_pinned_get_request",
        lambda url, headers, timeout_seconds, read_body, max_bytes: observed_headers.append(
            headers
        )
        or type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {"Content-Type": "text/html; charset=utf-8"},
                "body": b"<html>hello</html>",
            },
        )(),
    )

    document = SimpleHtmlFetcher().fetch("https://example.org/login")

    assert document is not None
    assert document.content == "<html>hello</html>"
    assert document.source_url == "https://example.org/login"
    assert observed_headers == [
        {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Verifiko/1.0",
        }
    ]


def test_html_fetcher_allows_per_request_user_agent_override(monkeypatch) -> None:
    observed_headers: list[dict[str, str]] = []

    monkeypatch.setattr(
        "app.infrastructure.external_services.html.simple_html_fetcher.send_pinned_get_request",
        lambda url, headers, timeout_seconds, read_body, max_bytes: observed_headers.append(
            headers
        )
        or type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {"Content-Type": "text/html; charset=utf-8"},
                "body": b"<html>variant</html>",
            },
        )(),
    )

    document = SimpleHtmlFetcher().fetch(
        "https://example.org/login",
        user_agent="TestAgent/9.9",
    )

    assert document is not None
    assert observed_headers == [
        {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "TestAgent/9.9",
        }
    ]


def test_redirect_resolver_revalidates_each_redirect_hop(monkeypatch) -> None:
    calls: list[str] = []

    def fake_send(url, *, headers, timeout_seconds, read_body, max_bytes=None):
        calls.append(url)
        if url == "https://safe.example/start":
            return type(
                "Response",
                (),
                {
                    "status_code": 302,
                    "headers": {"Location": "https://rebind.example/private"},
                    "body": b"",
                },
            )()
        raise AssertionError("unexpected request")

    def fake_resolve(url: str):
        if url == "https://rebind.example/private":
            raise UnsafeOutboundTargetError(
                "Outbound target resolved to a private or special-use address and was blocked."
            )
        return SafeOutboundResolution(
            hostname="safe.example",
            port=443,
            ip_addresses=("203.0.113.10",),
        )

    monkeypatch.setattr(
        "app.infrastructure.external_services.redirects.http_redirect_resolver.send_pinned_get_request",
        fake_send,
    )
    monkeypatch.setattr(
        "app.infrastructure.external_services.redirects.http_redirect_resolver.resolve_safe_outbound_url",
        fake_resolve,
    )

    with pytest.raises(RedirectResolutionError):
        HttpRedirectResolver().resolve("https://safe.example/start")

    assert calls == ["https://safe.example/start"]


def test_tls_validator_connects_to_validated_ip_not_hostname(monkeypatch) -> None:
    observed_destinations: list[tuple[str, int]] = []
    observed_server_hostnames: list[str] = []

    class _FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeWrappedSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeContext:
        def wrap_socket(self, sock, server_hostname):
            observed_server_hostnames.append(server_hostname)
            return _FakeWrappedSocket()

    monkeypatch.setattr(
        "app.infrastructure.external_services.tls.tls_client.resolve_safe_outbound_host",
        lambda hostname, port: SafeOutboundResolution(
            hostname="safe.example",
            port=443,
            ip_addresses=("203.0.113.10",),
        ),
    )
    monkeypatch.setattr(
        "app.infrastructure.external_services.tls.tls_client.socket.create_connection",
        lambda destination, timeout: observed_destinations.append(destination)
        or _FakeSocket(),
    )
    monkeypatch.setattr(
        "app.infrastructure.external_services.tls.tls_client.ssl.create_default_context",
        lambda: _FakeContext(),
    )

    result = SocketTlsValidator().validate_hostname("safe.example", 443)

    assert result.is_valid is True
    assert observed_destinations == [("203.0.113.10", 443)]
    assert observed_server_hostnames == ["safe.example"]


def test_infrastructure_lookup_reuses_validated_addresses_without_second_resolution(
    monkeypatch,
) -> None:
    reverse_queries: list[str] = []

    monkeypatch.setattr(
        "app.infrastructure.external_services.dns.socket_infrastructure_lookup.resolve_safe_outbound_host",
        lambda hostname, port: SafeOutboundResolution(
            hostname="safe.example",
            port=443,
            ip_addresses=("203.0.113.10", "203.0.113.11"),
        ),
    )

    def fail_getaddrinfo(*args, **kwargs):
        raise AssertionError(
            "lookup should not re-resolve hostnames after safety validation"
        )

    monkeypatch.setattr(
        "app.infrastructure.external_services.dns.socket_infrastructure_lookup.socket.getaddrinfo",
        fail_getaddrinfo,
    )
    monkeypatch.setattr(
        "app.infrastructure.external_services.dns.socket_infrastructure_lookup.socket.gethostbyaddr",
        lambda ip: reverse_queries.append(ip) or (f"ptr-{ip}.example", [], []),
    )

    profile = SocketInfrastructureLookup(max_reverse_lookups=2).lookup(
        "safe.example", 443
    )

    assert profile.queried_host == "safe.example"
    assert tuple(address.ip_address for address in profile.resolved_addresses) == (
        "203.0.113.10",
        "203.0.113.11",
    )
    assert reverse_queries == ["203.0.113.10", "203.0.113.11"]
