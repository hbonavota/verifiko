import socket

import pytest

from app.infrastructure.external_services.outbound_target_guard import (
    SafeOutboundResolution,
    UnsafeOutboundTargetError,
    assert_safe_outbound_host,
    resolve_safe_outbound_host,
)

_GUARD = "app.infrastructure.external_services.outbound_target_guard"


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


def test_outbound_target_guard_retries_transient_resolver_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def flaky(hostname, port, type):
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError(16, "Device or resource busy")  # EBUSY, transient
        return [(None, None, None, None, ("8.8.8.8", port))]

    monkeypatch.setattr(f"{_GUARD}.socket.getaddrinfo", flaky)
    monkeypatch.setattr(f"{_GUARD}.time.sleep", lambda _seconds: None)

    resolution = resolve_safe_outbound_host("example.org", 443)

    assert resolution.ip_addresses == ("8.8.8.8",)
    assert calls["n"] == 3  # failed twice, succeeded on the third attempt


def test_outbound_target_guard_surfaces_persistent_resolver_error_as_unsafe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def always_busy(hostname, port, type):
        raise OSError(16, "Device or resource busy")

    monkeypatch.setattr(f"{_GUARD}.socket.getaddrinfo", always_busy)
    monkeypatch.setattr(f"{_GUARD}.time.sleep", lambda _seconds: None)

    # Never a raw OSError / 500: a clean policy error the API maps to a 4xx.
    with pytest.raises(UnsafeOutboundTargetError):
        resolve_safe_outbound_host("example.org", 443)


def test_outbound_target_guard_does_not_retry_name_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def gai(hostname, port, type):
        calls["n"] += 1
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(f"{_GUARD}.socket.getaddrinfo", gai)

    with pytest.raises(UnsafeOutboundTargetError):
        resolve_safe_outbound_host("does-not-exist.example", 443)
    assert calls["n"] == 1  # genuine NXDOMAIN is terminal, not retried
