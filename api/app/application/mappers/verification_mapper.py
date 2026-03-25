from app.application.dto.verification_dto import AnalysisSignalDTO, RiskAssessmentDTO, VerificationDTO
from app.domain.entities.verification import Verification
from app.domain.services.scoring_policies import SEVERITY_MULTIPLIERS


class VerificationMapper:
    @staticmethod
    def to_dto(verification: Verification) -> VerificationDTO:
        risk_assessment_dto: RiskAssessmentDTO | None = None
        if verification.risk_assessment is not None:
            risk_assessment_dto = RiskAssessmentDTO(
                score=verification.risk_assessment.score.rounded(),
                risk_level=verification.risk_assessment.risk_level.value,
                verdict=verification.risk_assessment.verdict.value,
                summary=verification.risk_assessment.summary,
                top_signals=verification.risk_assessment.top_signals,
                category_breakdown=verification.risk_assessment.category_breakdown,
                terminal_override=verification.risk_assessment.terminal_override,
                terminal_reason=verification.risk_assessment.terminal_reason,
                calculation_version=verification.risk_assessment.calculation_version,
                calculated_at=verification.risk_assessment.calculated_at.isoformat(),
            )

        signal_dtos = tuple(
            AnalysisSignalDTO(
                id=str(signal.id),
                signal_type=signal.signal_type.value,
                category=signal.category.value,
                severity=signal.severity.value,
                confidence=signal.confidence.rounded(),
                detected=signal.detected,
                title=signal.title,
                description=signal.description,
                evidence=signal.evidence,
                source=signal.source,
                base_weight=signal.base_weight,
                score_contribution=round(
                    signal.base_weight * SEVERITY_MULTIPLIERS[signal.severity] * signal.confidence.as_ratio,
                    2,
                ),
                tags=signal.tags,
                created_at=signal.created_at.isoformat(),
            )
            for signal in verification.signals
        )

        return VerificationDTO(
            id=str(verification.id),
            target_type=verification.target_type.value,
            original_input=verification.original_input,
            normalized_input=verification.normalized_input.normalized,
            status=verification.status.value,
            signals=signal_dtos,
            risk_assessment=risk_assessment_dto,
            created_at=verification.created_at.isoformat(),
            updated_at=verification.updated_at.isoformat(),
            completed_at=verification.completed_at.isoformat() if verification.completed_at else None,
            calculation_version=verification.calculation_version,
        )
