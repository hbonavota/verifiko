import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeOutboundTargetError(Exception):
    """Raised when an outbound target is blocked by network safety policy."""


_BLOCKED_HOST_SUFFIXES = (".internal", ".local", ".localhost", ".home.arpa")


def assert_safe_outbound_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeOutboundTargetError("Only HTTP and HTTPS outbound targets are allowed.")
    if not parsed.hostname:
        raise UnsafeOutboundTargetError("Outbound target host is required.")

    assert_safe_outbound_host(parsed.hostname, parsed.port)


def assert_safe_outbound_host(hostname: str, port: int | None = None) -> None:
    normalized_host = hostname.strip().lower().rstrip(".")
    if not normalized_host:
        raise UnsafeOutboundTargetError("Outbound target host is required.")
    if normalized_host == "localhost" or normalized_host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeOutboundTargetError(
            "Outbound target is a local or special-use hostname and was blocked."
        )
    if "." not in normalized_host and not _looks_like_ip_address(normalized_host):
        raise UnsafeOutboundTargetError(
            "Outbound target uses a single-label hostname and was blocked."
        )

    for resolved_ip in _resolve_host_addresses(normalized_host, port):
        if not resolved_ip.is_global:
            raise UnsafeOutboundTargetError(
                "Outbound target resolved to a private or special-use address and was blocked."
            )


def _resolve_host_addresses(
    hostname: str,
    port: int | None,
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        addrinfo = socket.getaddrinfo(
            hostname,
            port or 443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeOutboundTargetError(
            "Outbound target host could not be resolved for safety validation."
        ) from exc

    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for _, _, _, _, sockaddr in addrinfo:
        addresses.add(ipaddress.ip_address(sockaddr[0]))
    return addresses


def _looks_like_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
