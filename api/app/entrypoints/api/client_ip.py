from ipaddress import IPv4Network, IPv6Network, ip_address
from typing import Sequence

from fastapi import Request


def resolve_client_ip(
    request: Request,
    *,
    trusted_proxy_networks: Sequence[IPv4Network | IPv6Network],
) -> str:
    peer_host = _peer_host(request)
    if peer_host is None:
        return "anonymous"

    if not _is_trusted_proxy(peer_host, trusted_proxy_networks):
        return peer_host

    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return peer_host

    original_client = forwarded_for.split(",", 1)[0].strip()
    if not original_client:
        return peer_host

    try:
        return ip_address(original_client).compressed
    except ValueError:
        return peer_host


def _peer_host(request: Request) -> str | None:
    client = request.client
    if client is None or not client.host:
        return None
    return client.host


def _is_trusted_proxy(
    peer_host: str,
    trusted_proxy_networks: Sequence[IPv4Network | IPv6Network],
) -> bool:
    try:
        peer_ip = ip_address(peer_host)
    except ValueError:
        return False

    return any(peer_ip in network for network in trusted_proxy_networks)
