from dataclasses import dataclass

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.services.scoring_policies import SEVERITY_MULTIPLIERS


@dataclass(frozen=True, slots=True)
class ExplanationFactor:
    signal_type: str
    title: str
    source: str
    severity: str
    score_contribution: float
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExplanationStageTrace:
    stage: str
    source: str
    status: str
    signal_count: int
    signal_titles: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskExplanation:
    headline: str
    decision_basis: str
    primary_factors: tuple[ExplanationFactor, ...]
    analysis_trace: tuple[ExplanationStageTrace, ...]
    coverage_warnings: tuple[str, ...]


class RiskExplanationBuilder:
    @staticmethod
    def build(verification: Verification) -> RiskExplanation | None:
        assessment = verification.risk_assessment
        if assessment is None:
            return None

        ranked_signals = sorted(
            verification.signals,
            key=RiskExplanationBuilder._score_contribution,
            reverse=True,
        )
        primary_factors = tuple(
            ExplanationFactor(
                signal_type=signal.signal_type.value,
                title=signal.title,
                source=signal.source,
                severity=signal.severity.value,
                score_contribution=RiskExplanationBuilder._score_contribution(signal),
                evidence=signal.evidence,
            )
            for signal in ranked_signals[:3]
        )

        headline = RiskExplanationBuilder._headline(assessment, primary_factors)
        decision_basis = RiskExplanationBuilder._decision_basis(assessment, primary_factors)
        analysis_trace = RiskExplanationBuilder._analysis_trace(verification)

        return RiskExplanation(
            headline=headline,
            decision_basis=decision_basis,
            primary_factors=primary_factors,
            analysis_trace=analysis_trace,
            coverage_warnings=assessment.analysis_warnings,
        )

    @staticmethod
    def _headline(
        assessment: RiskAssessment,
        primary_factors: tuple[ExplanationFactor, ...],
    ) -> str:
        if assessment.terminal_override:
            return "The result was forced to a terminal malicious outcome by trusted backend intelligence."
        if not primary_factors:
            return f"The engine produced a {assessment.verdict.value.lower()} outcome without high-confidence driver signals."
        trust_context_factors = tuple(
            factor for factor in primary_factors if factor.score_contribution == 0
        )
        if assessment.risk_level.value == "SAFE" and trust_context_factors:
            drivers = ", ".join(factor.title for factor in trust_context_factors[:2])
            return (
                f"The engine produced a {assessment.verdict.value.lower()} outcome supported by {drivers}."
            )

        drivers = ", ".join(factor.title for factor in primary_factors[:2])
        return (
            f"The engine produced a {assessment.verdict.value.lower()} outcome driven by {drivers}."
        )

    @staticmethod
    def _decision_basis(
        assessment: RiskAssessment,
        primary_factors: tuple[ExplanationFactor, ...],
    ) -> str:
        trust_context_factors = tuple(
            factor for factor in primary_factors if factor.score_contribution == 0
        )
        category_summary = ", ".join(
            f"{category}={penalty:.2f}"
            for category, penalty in sorted(
                assessment.category_breakdown.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if penalty > 0
        )
        if not category_summary:
            category_summary = "no category penalties recorded"
        if trust_context_factors and category_summary == "no category penalties recorded":
            return (
                f"Score {assessment.score.rounded()} mapped to {assessment.risk_level.value.lower()} "
                f"risk with {category_summary}. Supporting trust context: "
                f"{', '.join(factor.title for factor in trust_context_factors[:2])}."
            )

        if not primary_factors:
            return (
                f"Score {assessment.score.rounded()} mapped to {assessment.risk_level.value.lower()} "
                f"risk with {category_summary}."
            )

        return (
            f"Score {assessment.score.rounded()} mapped to {assessment.risk_level.value.lower()} "
            f"risk. Main contributing categories: {category_summary}."
        )

    @staticmethod
    def _score_contribution(signal: AnalysisSignal) -> float:
        return round(
            signal.base_weight * SEVERITY_MULTIPLIERS[signal.severity] * signal.confidence.as_ratio,
            2,
        )

    @staticmethod
    def _analysis_trace(verification: Verification) -> tuple[ExplanationStageTrace, ...]:
        if verification.risk_assessment is None:
            return ()

        if verification.risk_assessment.analysis_trace:
            return tuple(
                ExplanationStageTrace(
                    stage=stage.stage,
                    source=stage.source,
                    status=stage.status,
                    signal_count=stage.signal_count,
                    signal_titles=stage.signal_titles,
                    warnings=stage.warnings,
                )
                for stage in verification.risk_assessment.analysis_trace
            )

        grouped: dict[str, list[AnalysisSignal]] = {}
        for signal in verification.signals:
            grouped.setdefault(signal.source, []).append(signal)

        return tuple(
            ExplanationStageTrace(
                stage=source,
                source=source,
                status="signals_detected",
                signal_count=len(signals),
                signal_titles=tuple(signal.title for signal in signals[:3]),
                warnings=(),
            )
            for source, signals in grouped.items()
        )
