from uuid import UUID

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.target_type import TargetType
from app.domain.enums.verdict_type import VerdictType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl
from app.domain.value_objects.verification_id import VerificationId
from app.infrastructure.persistence.models.base_model import (
    RiskAssessmentModel,
    SignalModel,
    VerificationModel,
)


class VerificationModelMapper:
    @staticmethod
    def to_model(verification: Verification) -> VerificationModel:
        model = VerificationModel(id=str(verification.id))
        VerificationModelMapper.update_model(model, verification)
        return model

    @staticmethod
    def update_model(model: VerificationModel, verification: Verification) -> VerificationModel:
        model.target_type = verification.target_type.value
        model.original_input = verification.original_input
        model.normalized_input = verification.normalized_input.normalized
        model.status = verification.status.value
        model.created_at = verification.created_at
        model.updated_at = verification.updated_at
        model.completed_at = verification.completed_at
        model.calculation_version = verification.calculation_version
        model.signals = [VerificationModelMapper._signal_to_model(signal) for signal in verification.signals]
        model.risk_assessment = VerificationModelMapper._risk_assessment_to_model(
            verification.risk_assessment
        )
        return model

    @staticmethod
    def to_domain(model: VerificationModel) -> Verification:
        parsed_normalized_url = NormalizedUrl.from_raw(model.normalized_input)
        normalized_input = NormalizedUrl(
            raw=model.original_input,
            normalized=model.normalized_input,
            scheme=parsed_normalized_url.scheme,
            host=parsed_normalized_url.host,
            ascii_host=parsed_normalized_url.ascii_host,
            port=parsed_normalized_url.port,
            path=parsed_normalized_url.path,
            query=parsed_normalized_url.query,
            fragment=parsed_normalized_url.fragment,
            decoded_path=parsed_normalized_url.decoded_path,
            decoded_query=parsed_normalized_url.decoded_query,
            decoded_fragment=parsed_normalized_url.decoded_fragment,
            registered_domain=parsed_normalized_url.registered_domain,
            subdomain=parsed_normalized_url.subdomain,
            is_ip_address=parsed_normalized_url.is_ip_address,
            contains_unicode=parsed_normalized_url.contains_unicode,
            contains_punycode=parsed_normalized_url.contains_punycode,
            contains_zero_width_chars=parsed_normalized_url.contains_zero_width_chars,
            has_userinfo=parsed_normalized_url.has_userinfo,
            userinfo=parsed_normalized_url.userinfo,
        )

        return Verification(
            id=VerificationId.from_string(model.id),
            target_type=TargetType(model.target_type),
            original_input=model.original_input,
            normalized_input=normalized_input,
            status=VerificationStatus(model.status),
            signals=[VerificationModelMapper._signal_to_domain(signal) for signal in model.signals],
            risk_assessment=VerificationModelMapper._risk_assessment_to_domain(model.risk_assessment),
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
            calculation_version=model.calculation_version,
        )

    @staticmethod
    def _signal_to_model(signal: AnalysisSignal) -> SignalModel:
        return SignalModel(
            id=str(signal.id),
            signal_type=signal.signal_type.value,
            category=signal.category.value,
            severity=signal.severity.value,
            confidence=signal.confidence.value,
            detected=signal.detected,
            title=signal.title,
            description=signal.description,
            evidence=list(signal.evidence),
            source=signal.source,
            base_weight=signal.base_weight,
            tags=list(signal.tags),
            created_at=signal.created_at,
        )

    @staticmethod
    def _signal_to_domain(model: SignalModel) -> AnalysisSignal:
        return AnalysisSignal(
            id=UUID(model.id),
            signal_type=SignalType(model.signal_type),
            category=SignalCategory(model.category),
            severity=SignalSeverity(model.severity),
            confidence=ConfidenceScore(model.confidence),
            detected=model.detected,
            title=model.title,
            description=model.description,
            evidence=tuple(model.evidence or []),
            source=model.source,
            base_weight=model.base_weight,
            tags=tuple(model.tags or []),
            created_at=model.created_at,
        )

    @staticmethod
    def _risk_assessment_to_model(
        risk_assessment: RiskAssessment | None,
    ) -> RiskAssessmentModel | None:
        if risk_assessment is None:
            return None

        return RiskAssessmentModel(
            score=risk_assessment.score.value,
            risk_level=risk_assessment.risk_level.value,
            verdict=risk_assessment.verdict.value,
            summary=risk_assessment.summary,
            top_signals=list(risk_assessment.top_signals),
            category_breakdown=risk_assessment.category_breakdown,
            terminal_override=risk_assessment.terminal_override,
            terminal_reason=risk_assessment.terminal_reason,
            calculation_version=risk_assessment.calculation_version,
            calculated_at=risk_assessment.calculated_at,
        )

    @staticmethod
    def _risk_assessment_to_domain(
        model: RiskAssessmentModel | None,
    ) -> RiskAssessment | None:
        if model is None:
            return None

        return RiskAssessment(
            score=ConfidenceScore(model.score),
            risk_level=RiskLevel(model.risk_level),
            verdict=VerdictType(model.verdict),
            summary=model.summary,
            top_signals=tuple(model.top_signals or []),
            category_breakdown=dict(model.category_breakdown or {}),
            terminal_override=model.terminal_override,
            terminal_reason=model.terminal_reason,
            calculation_version=model.calculation_version,
            calculated_at=model.calculated_at,
        )
