from dataclasses import dataclass
from typing import Any

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.i18n.resolver import resolve_message
from app.domain.services.scoring_policies import SEVERITY_MULTIPLIERS

_DOMINANT_EXPLANATION_CATEGORIES = {
    SignalCategory.NAVIGATION_BEHAVIOR,
    SignalCategory.CONTENT_BEHAVIOR,
    SignalCategory.DOMAIN_REPUTATION,
    SignalCategory.NETWORK_TRANSPORT,
}
_DOMINANT_EXPLANATION_REASON_KEYS = {
    SignalType.SUSPICIOUS_REDIRECT_CHAIN: "summary.reason.suspicious_redirect_chain",
    SignalType.LOW_INFORMATION_PAGE: "summary.reason.low_information_page",
    SignalType.CREDENTIAL_HARVEST_FORM: "summary.reason.credential_harvest_form",
    SignalType.SUSPICIOUS_LOGIN_INTERFACE: "summary.reason.suspicious_login_interface",
    SignalType.CONTENT_VARIATION_DETECTED: "summary.reason.content_variation_detected",
    SignalType.TLS_VALIDATION_FAILURE: "summary.reason.tls_validation_failure",
    SignalType.INSECURE_TRANSPORT: "summary.reason.insecure_transport",
    SignalType.BRAND_IMPERSONATION: "summary.reason.brand_impersonation",
    SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN: "summary.reason.suspicious_infrastructure_pattern",
}
_CATEGORY_LABELS = {
    SignalCategory.DOMAIN_REPUTATION.value: "domain reputation",
    SignalCategory.DOMAIN_STRUCTURE.value: "domain structure",
    SignalCategory.NETWORK_TRANSPORT.value: "network transport",
    SignalCategory.NAVIGATION_BEHAVIOR.value: "navigation behavior",
    SignalCategory.CONTENT_BEHAVIOR.value: "content behavior",
}


@dataclass(frozen=True, slots=True)
class ExplanationFactor:
    signal_type: str
    title: str
    message_key: str | None
    message_params: dict[str, Any]
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
                message_key=signal.message_key,
                message_params=signal.message_params,
                source=signal.source,
                severity=signal.severity.value,
                score_contribution=RiskExplanationBuilder._score_contribution(signal),
                evidence=signal.evidence,
            )
            for signal in ranked_signals[:3]
        )

        dominant_signal = RiskExplanationBuilder._select_dominant_explanation_signal(
            verification.signals
        )
        headline = RiskExplanationBuilder._headline(
            assessment,
            primary_factors,
            dominant_signal,
        )
        decision_basis = RiskExplanationBuilder._decision_basis(
            assessment,
            primary_factors,
            dominant_signal,
        )
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
        dominant_signal: AnalysisSignal | None,
    ) -> str:
        if assessment.terminal_override:
            return resolve_message("explanation.headline.terminal_override")
        if not primary_factors:
            return resolve_message(
                "explanation.headline.no_high_confidence",
                {"verdict": assessment.verdict.value.lower()},
            )
        trust_context_factors = tuple(
            factor for factor in primary_factors if factor.score_contribution == 0
        )
        if assessment.risk_level.value == "SAFE" and trust_context_factors:
            drivers = ", ".join(factor.title for factor in trust_context_factors[:2])
            return resolve_message(
                "explanation.headline.safe_with_trust_context",
                {
                    "verdict": assessment.verdict.value.lower(),
                    "drivers": drivers,
                },
            )

        if dominant_signal is not None and assessment.risk_level is not RiskLevel.SAFE:
            return resolve_message(
                "explanation.headline.primary_concern",
                {
                    "verdict": assessment.verdict.value.lower(),
                    "reason": resolve_message(
                        _DOMINANT_EXPLANATION_REASON_KEYS[dominant_signal.signal_type]
                    ),
                },
            )

        drivers = ", ".join(factor.title for factor in primary_factors[:2])
        return resolve_message(
            "explanation.headline.driven_by",
            {
                "verdict": assessment.verdict.value.lower(),
                "drivers": drivers,
            },
        )

    @staticmethod
    def _decision_basis(
        assessment: RiskAssessment,
        primary_factors: tuple[ExplanationFactor, ...],
        dominant_signal: AnalysisSignal | None,
    ) -> str:
        trust_context_factors = tuple(
            factor for factor in primary_factors if factor.score_contribution == 0
        )
        category_summary = ", ".join(
            f"{_localize_category_label(category)}={penalty:.2f}"
            for category, penalty in sorted(
                assessment.category_breakdown.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if penalty > 0
        )
        if not category_summary:
            category_summary = resolve_message("phrase.no_category_penalties_recorded")
        if trust_context_factors and category_summary == resolve_message("phrase.no_category_penalties_recorded"):
            return resolve_message(
                "explanation.decision_basis.with_trust_context",
                {
                    "score": assessment.score.rounded(),
                    "risk_level": assessment.risk_level.value.lower(),
                    "category_summary": category_summary,
                    "drivers": ", ".join(factor.title for factor in trust_context_factors[:2]),
                },
            )

        if dominant_signal is not None and assessment.risk_level is not RiskLevel.SAFE:
            return resolve_message(
                "explanation.decision_basis.primary_reason",
                {
                    "reason": resolve_message(
                        _DOMINANT_EXPLANATION_REASON_KEYS[dominant_signal.signal_type]
                    ),
                    "score": assessment.score.rounded(),
                    "risk_level": assessment.risk_level.value.lower(),
                    "category_summary": category_summary,
                },
            )

        if not primary_factors:
            return resolve_message(
                "explanation.decision_basis.no_primary_factors",
                {
                    "score": assessment.score.rounded(),
                    "risk_level": assessment.risk_level.value.lower(),
                    "category_summary": category_summary,
                },
            )

        return resolve_message(
            "explanation.decision_basis.main_categories",
            {
                "score": assessment.score.rounded(),
                "risk_level": assessment.risk_level.value.lower(),
                "category_summary": category_summary,
            },
        )

    @staticmethod
    def _score_contribution(signal: AnalysisSignal) -> float:
        return round(
            signal.base_weight * SEVERITY_MULTIPLIERS[signal.severity] * signal.confidence.as_ratio,
            2,
        )

    @staticmethod
    def _select_dominant_explanation_signal(
        signals: list[AnalysisSignal],
    ) -> AnalysisSignal | None:
        eligible = [
            signal
            for signal in signals
            if signal.detected
            and signal.severity in {SignalSeverity.HIGH, SignalSeverity.CRITICAL}
            and signal.confidence.value > 80
            and signal.category in _DOMINANT_EXPLANATION_CATEGORIES
            and signal.signal_type in _DOMINANT_EXPLANATION_REASON_KEYS
            and RiskExplanationBuilder._score_contribution(signal) > 0
        ]
        if not eligible:
            return None
        return max(eligible, key=RiskExplanationBuilder._score_contribution)

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


def _localize_category_label(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category.replace("_", " "))
