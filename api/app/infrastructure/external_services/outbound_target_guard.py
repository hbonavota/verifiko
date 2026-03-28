from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urlsplit

from app.domain.i18n.resolver import resolve_message


class UnsafeOutboundTargetError(Exception):
    """Raised when an outbound target is blocked by network safety policy."""


_BLOCKED_HOST_SUFFIXES = (".internal", ".local", ".localhost", ".home.arpa")


@dataclass(frozen=True, slots=True)
class SafeOutboundResolution:
    hostname: str
    port: int
    ip_addresses: tuple[str, ...]


def assert_safe_outbound_url(url: str) -> None:
    resolve_safe_outbound_url(url)


def resolve_safe_outbound_url(url: str) -> SafeOutboundResolution:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeOutboundTargetError(
            resolve_message("error.only_http_https_outbound_targets_allowed")
        )
    if not parsed.hostname:
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_host_required"))

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return resolve_safe_outbound_host(parsed.hostname, port)


def assert_safe_outbound_host(hostname: str, port: int | None = None) -> None:
    resolve_safe_outbound_host(hostname, port)


def resolve_safe_outbound_host(
    hostname: str,
    port: int | None = None,
) -> SafeOutboundResolution:
    normalized_host = hostname.strip().lower().rstrip(".")
    if not normalized_host:
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_host_required"))
    if normalized_host == "localhost" or normalized_host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_local_special_use_blocked"))
    if "." not in normalized_host and not _looks_like_ip_address(normalized_host):
        raise UnsafeOutboundTargetError(resolve_message("error.outbound_target_single_label_blocked"))

    resolved_port = port or 443
    addresses = _resolve_host_addresses(normalized_host, resolved_port)
    for resolved_ip in addresses:
        if not resolved_ip.is_global:
            raise UnsafeOutboundTargetError(
                resolve_message("error.outbound_target_private_special_use_address_blocked")
            )
    return SafeOutboundResolution(
        hostname=normalized_host,
        port=resolved_port,
        ip_addresses=tuple(str(address) for address in addresses),
    )


def _resolve_host_addresses(
    hostname: str,
    port: int | None,
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
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

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    seen: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for _, _, _, _, sockaddr in addrinfo:
        ip_address = ipaddress.ip_address(sockaddr[0])
        if ip_address in seen:
            continue
        seen.add(ip_address)
        addresses.append(ip_address)
    return tuple(addresses)


def _looks_like_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
