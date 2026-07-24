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


def test_deep_scan_detonates_everything_but_already_decided() -> None:
    policy = DetonationPolicy()
    for level in (RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM):
        assert policy.should_detonate(level, deep_scan_requested=True) is True
    for level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        assert policy.should_detonate(level, deep_scan_requested=True) is False
