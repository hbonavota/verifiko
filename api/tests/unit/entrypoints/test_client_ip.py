from ipaddress import ip_network
from types import SimpleNamespace

from app.entrypoints.api.client_ip import resolve_client_ip


def _request(*, client_host: str | None, forwarded_for: str | None = None):
    headers = {}
    if forwarded_for is not None:
        headers["x-forwarded-for"] = forwarded_for
    client = None if client_host is None else SimpleNamespace(host=client_host)
    return SimpleNamespace(headers=headers, client=client)


def test_resolve_client_ip_uses_peer_host_without_trusted_proxies() -> None:
    request = _request(client_host="198.51.100.10", forwarded_for="203.0.113.20")

    resolved = resolve_client_ip(request, trusted_proxy_networks=[])

    assert resolved == "198.51.100.10"


def test_resolve_client_ip_uses_original_x_forwarded_for_value_for_trusted_proxy() -> (
    None
):
    request = _request(
        client_host="203.0.113.10",
        forwarded_for="198.51.100.25, 203.0.113.10",
    )

    resolved = resolve_client_ip(
        request,
        trusted_proxy_networks=[ip_network("203.0.113.0/24")],
    )

    assert resolved == "198.51.100.25"


def test_resolve_client_ip_falls_back_to_peer_host_for_invalid_forwarded_for() -> None:
    request = _request(
        client_host="203.0.113.10",
        forwarded_for="not-an-ip, 198.51.100.25",
    )

    resolved = resolve_client_ip(
        request,
        trusted_proxy_networks=[ip_network("203.0.113.0/24")],
    )

    assert resolved == "203.0.113.10"
