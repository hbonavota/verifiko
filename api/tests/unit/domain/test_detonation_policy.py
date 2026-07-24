from app.domain.enums.risk_level import RiskLevel
from app.domain.services.detonation_policy import DetonationPolicy


def test_detonates_suspicious_middle_band() -> None:
    policy = DetonationPolicy()
    assert policy.should_detonate(RiskLevel.LOW) is True
    assert policy.should_detonate(RiskLevel.MEDIUM) is True


def test_skips_clearly_benign_and_already_decided() -> None:
    policy = DetonationPolicy()
    assert policy.should_detonate(RiskLevel.SAFE) is False
    assert policy.should_detonate(RiskLevel.HIGH) is False
    assert policy.should_detonate(RiskLevel.CRITICAL) is False


def test_explicit_deep_scan_always_detonates() -> None:
    policy = DetonationPolicy()
    for level in RiskLevel:
        assert policy.should_detonate(level, deep_scan_requested=True) is True
