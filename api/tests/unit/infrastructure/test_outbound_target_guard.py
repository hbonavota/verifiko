import pytest

from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
    assert_safe_outbound_host,
)


def test_outbound_target_guard_blocks_localhost() -> None:
    with pytest.raises(UnsafeOutboundTargetError):
        assert_safe_outbound_host("localhost", 80)


def test_outbound_target_guard_blocks_private_ip_targets() -> None:
    with pytest.raises(UnsafeOutboundTargetError):
        assert_safe_outbound_host("127.0.0.1", 80)
