import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.domain.i18n.resolver import resolve_message


class UnsafeOutboundTargetError(Exception):
    """Raised when an outbound target is blocked by network safety policy."""


_BLOCKED_HOST_SUFFIXES = (".internal", ".local", ".localhost", ".home.arpa")
_DNS_RESOLUTION_ATTEMPTS = 3
_DNS_RESOLUTION_BACKOFF_SECONDS = 0.05
# IPv6 transition forms carry an embedded IPv4. ``ipaddress.is_global`` judges
# them by the IPv6 prefix and can report them as global even when the embedded
# IPv4 is private/special-use — so a hostname that resolves to, say,
# ``64:ff9b::7f00:1`` (NAT64 of 127.0.0.1) could otherwise slip past the guard.
_NAT64_WELL_KNOWN_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")
_IPV4_COMPATIBLE_PREFIX = ipaddress.IPv6Network("::/96")


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
        raise UnsafeOutboundTargetError(
            resolve_message("error.outbound_target_host_required")
        )

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
        raise UnsafeOutboundTargetError(
            resolve_message("error.outbound_target_host_required")
        )
    if normalized_host == "localhost" or normalized_host.endswith(
        _BLOCKED_HOST_SUFFIXES
    ):
        raise UnsafeOutboundTargetError(
            resolve_message("error.outbound_target_local_special_use_blocked")
        )
    if "." not in normalized_host and not _looks_like_ip_address(normalized_host):
        raise UnsafeOutboundTargetError(
            resolve_message("error.outbound_target_single_label_blocked")
        )

    resolved_port = port or 443
    addresses = _resolve_host_addresses(normalized_host, resolved_port)
    for resolved_ip in addresses:
        if not resolved_ip.is_global or any(
            not embedded_ip.is_global
            for embedded_ip in _embedded_ipv4_addresses(resolved_ip)
        ):
            raise UnsafeOutboundTargetError(
                resolve_message(
                    "error.outbound_target_private_special_use_address_blocked"
                )
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
    addrinfo = _getaddrinfo_with_retry(hostname, port or 443)

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    seen: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for _, _, _, _, sockaddr in addrinfo:
        ip_address = ipaddress.ip_address(sockaddr[0])
        if ip_address in seen:
            continue
        seen.add(ip_address)
        addresses.append(ip_address)
    return tuple(addresses)


def _getaddrinfo_with_retry(hostname: str, port: int) -> list:
    """Resolve a hostname, tolerating transient resolver failures.

    ``socket.getaddrinfo`` can raise a plain ``OSError`` such as ``EBUSY``
    (Errno 16, "Device or resource busy") when the underlying DNS resolver is
    contended — notably under concurrent lookups on some serverless runtimes.
    That is transient, so we retry a few times with a short backoff. A genuine
    name-resolution failure (``gaierror``) is not retried. If resolution still
    fails, we surface it as an unsafe/unresolvable target (a clean 4xx) rather
    than an unhandled 500.
    """
    last_error: OSError | None = None
    for attempt in range(_DNS_RESOLUTION_ATTEMPTS):
        try:
            return socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise UnsafeOutboundTargetError(
                resolve_message(
                    "error.outbound_target_host_unresolved_for_safety_validation"
                )
            ) from exc
        except OSError as exc:
            last_error = exc
            if attempt < _DNS_RESOLUTION_ATTEMPTS - 1:
                time.sleep(_DNS_RESOLUTION_BACKOFF_SECONDS * (attempt + 1))
    raise UnsafeOutboundTargetError(
        resolve_message("error.outbound_target_host_unresolved_for_safety_validation")
    ) from last_error


def _looks_like_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _embedded_ipv4_addresses(
    address: "ipaddress.IPv4Address | ipaddress.IPv6Address",
) -> tuple[ipaddress.IPv4Address, ...]:
    """Return any IPv4 address embedded in an IPv6 transition form.

    Covers IPv4-mapped (``::ffff:a.b.c.d``), 6to4 (``2002::/16``), Teredo
    (``2001::/32``), the NAT64 well-known prefix (``64:ff9b::/96``) and the
    deprecated IPv4-compatible form (``::a.b.c.d``). The caller re-validates each
    embedded IPv4 with ``is_global`` so a non-global IPv4 cannot be smuggled past
    the guard inside an IPv6 the prefix alone makes look global.
    """
    if not isinstance(address, ipaddress.IPv6Address):
        return ()

    embedded: list[ipaddress.IPv4Address] = []
    if address.ipv4_mapped is not None:
        embedded.append(address.ipv4_mapped)
    if address.sixtofour is not None:
        embedded.append(address.sixtofour)
    if address.teredo is not None:
        server_ip, client_ip = address.teredo
        embedded.extend((server_ip, client_ip))
    if address in _NAT64_WELL_KNOWN_PREFIX:
        embedded.append(ipaddress.IPv4Address(int(address) & 0xFFFFFFFF))
    if address in _IPV4_COMPATIBLE_PREFIX:
        trailing_ipv4 = int(address) & 0xFFFFFFFF
        if trailing_ipv4 not in (0, 1):  # exclude :: and ::1 (is_global handles them)
            embedded.append(ipaddress.IPv4Address(trailing_ipv4))
    return tuple(embedded)
