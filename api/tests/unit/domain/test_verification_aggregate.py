from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.verification import Verification
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.value_objects.confidence_score import ConfidenceScore


def test_verification_completes_with_assessment() -> None:
    verification = Verification.create_url("https://verifiko.es")
    verification.set_analyzing()

    verification.add_signal(
        AnalysisSignal.create(
            signal_type=SignalType.NON_STANDARD_PORT_USAGE,
            category=SignalCategory.NETWORK_TRANSPORT,
            severity=SignalSeverity.MEDIUM,
            confidence=ConfidenceScore(80),
            title="Non standard port",
            description="Target uses uncommon HTTPS port",
            source="network-check",
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.NON_STANDARD_PORT_USAGE],
        )
    )

    assessment = verification.complete(RiskScoringEngine())

    assert verification.status is VerificationStatus.COMPLETED
    assert verification.risk_assessment is assessment
    assert verification.completed_at is not None
