from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlunsplit

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.enums.target_type import TargetType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.normalized_url import NormalizedUrl
from app.domain.value_objects.user_id import UserId
from app.domain.value_objects.verification_id import VerificationId


@dataclass(slots=True)
class Verification:
    id: VerificationId
    user_id: UserId | None
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
        user_id: UserId | None = None,
        calculation_version: str = "v1",
    ) -> "Verification":
        now = datetime.now(UTC)
        return Verification(
            id=verification_id or VerificationId.new(),
            user_id=user_id,
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
        self.updated_at = datetime.now(UTC)

    def add_signal(self, signal: AnalysisSignal) -> None:
        self.signals.append(signal)
        self.updated_at = datetime.now(UTC)

    def add_signals(self, signals: list[AnalysisSignal]) -> None:
        self.signals.extend(signals)
        self.updated_at = datetime.now(UTC)

    def complete(self, scoring_service: ScoringService) -> RiskAssessment:
        assessment = scoring_service.calculate(self.signals, self.calculation_version)
        now = datetime.now(UTC)
        self.risk_assessment = assessment
        self.status = VerificationStatus.COMPLETED
        self.updated_at = now
        self.completed_at = now
        return assessment

    def fail(self) -> None:
        self.status = VerificationStatus.FAILED
        self.updated_at = datetime.now(UTC)

    def redact_sensitive_input(self) -> None:
        if not (
            self.normalized_input.query
            or self.normalized_input.fragment
            or self.normalized_input.has_userinfo
        ):
            return

        netloc = self.normalized_input.ascii_host
        if self.normalized_input.port is not None:
            netloc = f"{netloc}:{self.normalized_input.port}"

        redacted_url = urlunsplit(
            (
                self.normalized_input.scheme,
                netloc,
                self.normalized_input.path or "/",
                "",
                "",
            )
        )
        self.original_input = redacted_url
        self.normalized_input = NormalizedUrl.from_raw(redacted_url)
        self.updated_at = datetime.now(UTC)
