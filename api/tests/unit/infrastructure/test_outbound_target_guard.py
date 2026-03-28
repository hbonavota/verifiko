import pytest

from app.infrastructure.external_services.outbound_target_guard import (
    SafeOutboundResolution,
    UnsafeOutboundTargetError,
    assert_safe_outbound_host,
    resolve_safe_outbound_host,
)


def test_outbound_target_guard_blocks_localhost() -> None:
    with pytest.raises(UnsafeOutboundTargetError):
        assert_safe_outbound_host("localhost", 80)


def test_outbound_target_guard_blocks_private_ip_targets() -> None:
    with pytest.raises(UnsafeOutboundTargetError):
        assert_safe_outbound_host("127.0.0.1", 80)


def test_outbound_target_guard_resolves_public_host_to_validated_ips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_getaddrinfo(hostname, port, type):
        assert hostname == "example.org"
        assert port == 443
        return [
            (None, None, None, None, ("8.8.8.8", 443)),
            (None, None, None, None, ("1.1.1.1", 443)),
        ]

    monkeypatch.setattr(
        "app.infrastructure.external_services.outbound_target_guard.socket.getaddrinfo",
        fake_getaddrinfo,
    )

    resolution = resolve_safe_outbound_host("example.org", 443)

    assert resolution == SafeOutboundResolution(
        hostname="example.org",
        port=443,
        ip_addresses=("8.8.8.8", "1.1.1.1"),
    )


def test_outbound_target_guard_blocks_resolution_to_private_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.infrastructure.external_services.outbound_target_guard.socket.getaddrinfo",
        lambda hostname, port, type: [(None, None, None, None, ("127.0.0.1", port))],
    )

    with pytest.raises(UnsafeOutboundTargetError):
        resolve_safe_outbound_host("rebind.example", 443)
