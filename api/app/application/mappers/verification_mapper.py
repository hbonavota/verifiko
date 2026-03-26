from app.application.dto.verification_dto import (
    AnalysisSignalDTO,
    AnalysisTraceDTO,
    AnalysisStageTraceDTO,
    CompoundRuleDeltaDTO,
    ExplanationFactorDTO,
    RiskAssessmentDTO,
    RiskExplanationDTO,
    ScoreBreakdownDTO,
    SignalContributionDTO,
    VerificationDTO,
)
from app.application.services.analysis_trace_builder import AnalysisTraceBuilder
from app.application.services.risk_explanation_builder import RiskExplanationBuilder
from app.domain.entities.analysis_trace import AnalysisTrace
from app.domain.entities.verification import Verification
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.domain.services.score_breakdown_builder import build_score_breakdown
from app.domain.services.scoring_policies import SEVERITY_MULTIPLIERS


class VerificationMapper:
    @staticmethod
    def to_dto(
        verification: Verification,
        trace: AnalysisTrace | None = None,
    ) -> VerificationDTO:
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

        risk_assessment_dto: RiskAssessmentDTO | None = None
        score_breakdown_dto: ScoreBreakdownDTO | None = None
        if verification.risk_assessment is not None:
            explanation = RiskExplanationBuilder.build(verification)
            if explanation is None:
                raise ValueError("Risk explanation must be available when risk assessment exists.")
            score_breakdown = verification.risk_assessment.score_breakdown
            if score_breakdown is None:
                engine = RiskScoringEngine()
                score_breakdown = build_score_breakdown(
                    verification.signals,
                    engine._compound_rules,
                    final_score=verification.risk_assessment.score.value,
                )
            if score_breakdown is None:
                raise ValueError("Score breakdown must be available when risk assessment exists.")
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
                analysis_warnings=verification.risk_assessment.analysis_warnings,
                analysis_trace=tuple(
                    AnalysisStageTraceDTO(
                        stage=stage.stage,
                        source=stage.source,
                        status=stage.status,
                        signal_count=stage.signal_count,
                        signal_titles=stage.signal_titles,
                        warnings=stage.warnings,
                    )
                    for stage in verification.risk_assessment.analysis_trace
                ),
                explanation=RiskExplanationDTO(
                    headline=explanation.headline,
                    decision_basis=explanation.decision_basis,
                    primary_factors=tuple(
                        ExplanationFactorDTO(
                            signal_type=factor.signal_type,
                            title=factor.title,
                            source=factor.source,
                            severity=factor.severity,
                            score_contribution=factor.score_contribution,
                            evidence=factor.evidence,
                        )
                        for factor in explanation.primary_factors
                    ),
                    analysis_trace=tuple(
                        AnalysisStageTraceDTO(
                            stage=stage.stage,
                            source=stage.source,
                            status=stage.status,
                            signal_count=stage.signal_count,
                            signal_titles=stage.signal_titles,
                            warnings=stage.warnings,
                        )
                        for stage in explanation.analysis_trace
                    ),
                    coverage_warnings=explanation.coverage_warnings,
                ),
                calculated_at=verification.risk_assessment.calculated_at.isoformat(),
            )
            score_breakdown_dto = ScoreBreakdownDTO(
                base_score=score_breakdown.base_score,
                signal_contributions=tuple(
                    SignalContributionDTO(
                        signal_type=entry.signal_type,
                        base_weight=entry.base_weight,
                        confidence=entry.confidence,
                        impact=entry.impact,
                    )
                    for entry in score_breakdown.signal_contributions
                ),
                compound_rules_applied=tuple(
                    CompoundRuleDeltaDTO(
                        rule_name=entry.rule_name,
                        delta=entry.delta,
                    )
                    for entry in score_breakdown.compound_rules_applied
                ),
                final_score=score_breakdown.final_score,
            )

        resolved_trace = trace or AnalysisTraceBuilder.from_signals(verification.signals)
        signals_by_source = {
            source: tuple(dto for dto in signal_dtos if dto.source == source)
            for source in resolved_trace.layers_executed
            if any(dto.source == source for dto in signal_dtos)
        }
        trace_dto = AnalysisTraceDTO(
            layers_executed=resolved_trace.layers_executed,
            signals_by_source=signals_by_source,
            total_signals=resolved_trace.total_signals,
        )

        return VerificationDTO(
            id=str(verification.id),
            target_type=verification.target_type.value,
            original_input=verification.original_input,
            normalized_input=verification.normalized_input.normalized,
            status=verification.status.value,
            signals=signal_dtos,
            risk_assessment=risk_assessment_dto,
            trace=trace_dto,
            score_breakdown=score_breakdown_dto,
            created_at=verification.created_at.isoformat(),
            updated_at=verification.updated_at.isoformat(),
            completed_at=verification.completed_at.isoformat() if verification.completed_at else None,
            calculation_version=verification.calculation_version,
        )
