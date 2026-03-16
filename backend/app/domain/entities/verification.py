from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.enums.target_type import TargetType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.normalized_url import NormalizedUrl
from app.domain.value_objects.verification_id import VerificationId


@dataclass(slots=True)
class Verification:
    id: VerificationId
    target_type: TargetType
    original_input: str
    normalized_input: NormalizedUrl
    status: VerificationStatus
    signals: list[AnalysisSignal]
    risk_assessment: RiskAssessment | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    calculation_version: str

    @staticmethod
    def create_url(
        input_url: str,
        verification_id: VerificationId | None = None,
        calculation_version: str = "v1",
    ) -> "Verification":
        now = datetime.now(timezone.utc)
        return Verification(
            id=verification_id or VerificationId.new(),
            target_type=TargetType.URL,
            original_input=input_url,
            normalized_input=NormalizedUrl.from_raw(input_url),
            status=VerificationStatus.PENDING,
            signals=[],
            risk_assessment=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
            calculation_version=calculation_version,
        )

    def set_analyzing(self) -> None:
        self.status = VerificationStatus.ANALYZING
        self.updated_at = datetime.now(timezone.utc)

    def add_signal(self, signal: AnalysisSignal) -> None:
        self.signals.append(signal)
        self.updated_at = datetime.now(timezone.utc)

    def add_signals(self, signals: list[AnalysisSignal]) -> None:
        self.signals.extend(signals)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, scoring_service: ScoringService) -> RiskAssessment:
        assessment = scoring_service.calculate(self.signals, self.calculation_version)
        now = datetime.now(timezone.utc)
        self.risk_assessment = assessment
        self.status = VerificationStatus.COMPLETED
        self.updated_at = now
        self.completed_at = now
        return assessment

    def fail(self) -> None:
        self.status = VerificationStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)
