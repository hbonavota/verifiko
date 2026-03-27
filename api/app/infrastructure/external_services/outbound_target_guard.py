import ipaddress
import socket
from urllib.parse import urlsplit

from app.domain.i18n.resolver import resolve_message


class UnsafeOutboundTargetError(Exception):
    """Raised when an outbound target is blocked by network safety policy."""


_BLOCKED_HOST_SUFFIXES = (".internal", ".local", ".localhost", ".home.arpa")


def assert_safe_outbound_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeOutboundTargetError(
            resolve_message("error.only_http_https_outbound_targets_allowed")
        )
    if not parsed.hostname:
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_host_required"))

    assert_safe_outbound_host(parsed.hostname, parsed.port)


def assert_safe_outbound_host(hostname: str, port: int | None = None) -> None:
    normalized_host = hostname.strip().lower().rstrip(".")
    if not normalized_host:
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_host_required"))
    if normalized_host == "localhost" or normalized_host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_local_special_use_blocked"))
    if "." not in normalized_host and not _looks_like_ip_address(normalized_host):
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_single_label_blocked"))

    for resolved_ip in _resolve_host_addresses(normalized_host, port):
        if not resolved_ip.is_global:
            raise UnsafeOutboundTargetError(
                resolve_message("error.outbound_target_private_special_use_address_blocked")
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
            resolve_message("error.outbound_target_host_unresolved_for_safety_validation")
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
