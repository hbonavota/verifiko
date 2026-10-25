from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verdict_type import VerdictType
from app.domain.i18n.resolver import resolve_message
from app.domain.services.compound_rules import (
    BrandNewLookalikeDomainRule,
    BrandTyposquattingRule,
    CompoundRule,
    CredentialExfiltrationRule,
    CredentialLurePatternRule,
    DeceptiveBrandSubdomainRule,
    EmailFraudStagingPatternRule,
    EvidenceLightCleanResultRule,
    InfrastructureBackedCredentialLureRule,
    LowInformationLandingPageRule,
    RedirectedCredentialLureRule,
    RedirectedDeceptionPatternRule,
    RedirectedLowInformationDestinationRule,
    ReputableDomainSupportRule,
    ShortenedCredentialLureRule,
    ShortenedRedirectedLureRule,
    detected_types,
)
from app.domain.services.score_breakdown_builder import build_score_breakdown
from app.domain.services.scoring_policies import CATEGORY_CAPS, SEVERITY_MULTIPLIERS
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.confidence_score import ConfidenceScore

_DOMINANT_SUMMARY_CATEGORIES = {
    SignalCategory.NAVIGATION_BEHAVIOR,
    SignalCategory.CONTENT_BEHAVIOR,
    SignalCategory.DOMAIN_REPUTATION,
    SignalCategory.NETWORK_TRANSPORT,
}
_DOMINANT_SUMMARY_REASON_KEYS = {
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


class RiskScoringEngine(ScoringService):
    def __init__(self, compound_rules: list[CompoundRule] | None = None) -> None:
        self._compound_rules = compound_rules or [
            BrandNewLookalikeDomainRule(),
            BrandTyposquattingRule(),
            CredentialExfiltrationRule(),
            CredentialLurePatternRule(),
            DeceptiveBrandSubdomainRule(),
            EmailFraudStagingPatternRule(),
            RedirectedDeceptionPatternRule(),
            ShortenedCredentialLureRule(),
            ShortenedRedirectedLureRule(),
            RedirectedCredentialLureRule(),
            InfrastructureBackedCredentialLureRule(),
            LowInformationLandingPageRule(),
            RedirectedLowInformationDestinationRule(),
            EvidenceLightCleanResultRule(),
            ReputableDomainSupportRule(),
        ]

    def calculate(
        self, signals: list[AnalysisSignal], calculation_version: str
    ) -> RiskAssessment:
        active_signals = [signal for signal in signals if signal.detected]
        if _is_terminal_blacklist(active_signals):
            final_score = ConfidenceScore(0)
            return RiskAssessment(
                score=final_score,
                risk_level=RiskLevel.CRITICAL,
                verdict=VerdictType.CONFIRMED_MALICIOUS,
                summary=resolve_message("summary.terminal_blacklist_override"),
                top_signals=_top_signal_titles(active_signals),
                category_breakdown={},
                terminal_override=True,
                terminal_reason="blacklist_match confidence >= 0.98",
                calculation_version=calculation_version,
                score_breakdown=build_score_breakdown(
                    active_signals,
                    self._compound_rules,
                    final_score=final_score.value,
                ),
            )

        raw_category_penalties: dict[str, float] = {}
        signal_penalties: list[tuple[str, float]] = []
        informational_signals: list[AnalysisSignal] = []

        for signal in active_signals:
            signal_penalty = _signal_penalty(signal)
            signal_penalties.append((signal.title, signal_penalty))
            if signal_penalty == 0:
                informational_signals.append(signal)
                continue
            key = signal.category.value
            raw_category_penalties[key] = (
                raw_category_penalties.get(key, 0.0) + signal_penalty
            )

        capped_category_penalties = {
            category.value: min(raw_category_penalties.get(category.value, 0.0), cap)
            for category, cap in CATEGORY_CAPS.items()
        }

        category_total_penalty = sum(capped_category_penalties.values())
        compound_penalty, triggered_rules = self._compound_penalty(active_signals)

        final_score_value = max(
            0.0, min(100.0, 100 - category_total_penalty - compound_penalty)
        )
        final_score = ConfidenceScore(final_score_value)

        risk_level = risk_level_for_score(final_score.value)
        verdict = verdict_for_level(risk_level)

        summary = resolve_message(
            "summary.risk_detected",
            {
                "risk_signal_count": len(active_signals) - len(informational_signals),
                "risk_level": risk_level.value.lower(),
                "category_total_penalty": category_total_penalty,
                "compound_penalty": compound_penalty,
            },
        )
        dominant_signal = _select_dominant_summary_signal(active_signals)
        top_signal_titles = _top_signal_titles_from_penalties(
            signal_penalties, max_items=3
        )
        if not top_signal_titles and informational_signals:
            top_signal_titles = tuple(
                signal.title for signal in informational_signals[:3]
            )
        if dominant_signal is not None and risk_level is not RiskLevel.SAFE:
            summary = resolve_message(
                "summary.primary_concern",
                {
                    "summary": summary,
                    "reason": resolve_message(
                        _DOMINANT_SUMMARY_REASON_KEYS[dominant_signal.signal_type]
                    ),
                },
            )
            if len(active_signals) - len(informational_signals) > 1:
                summary = resolve_message(
                    "summary.secondary_factors",
                    {"summary": summary},
                )
        if triggered_rules:
            summary = resolve_message(
                "summary.rules",
                {"summary": summary, "rule_count": len(triggered_rules)},
            )
        if informational_signals:
            summary = resolve_message(
                "summary.supporting_trust_context",
                {
                    "summary": summary,
                    "trust_context": ", ".join(
                        signal.title for signal in informational_signals[:2]
                    ),
                },
            )

        return RiskAssessment(
            score=final_score,
            risk_level=risk_level,
            verdict=verdict,
            summary=summary,
            top_signals=_top_signal_titles_from_penalties(signal_penalties)
            or tuple(signal.title for signal in informational_signals[:5]),
            category_breakdown=capped_category_penalties,
            terminal_override=False,
            terminal_reason=None,
            calculation_version=calculation_version,
            score_breakdown=build_score_breakdown(
                active_signals,
                self._compound_rules,
                final_score=final_score.value,
            ),
        )

    def _compound_penalty(
        self, signals: list[AnalysisSignal]
    ) -> tuple[float, list[str]]:
        types = detected_types(signals)
        total = 0.0
        triggered: list[str] = []
        for rule in self._compound_rules:
            penalty = rule.evaluate(types)
            if penalty is None:
                continue
            total += penalty
            triggered.append(rule.name)
        return total, triggered


def _signal_penalty(signal: AnalysisSignal) -> float:
    multiplier = SEVERITY_MULTIPLIERS[signal.severity]
    return signal.base_weight * multiplier * signal.confidence.as_ratio


def _select_dominant_summary_signal(
    signals: list[AnalysisSignal],
) -> AnalysisSignal | None:
    eligible = [
        signal
        for signal in signals
        if signal.detected
        and signal.severity in {SignalSeverity.HIGH, SignalSeverity.CRITICAL}
        and signal.confidence.value > 80
        and signal.category in _DOMINANT_SUMMARY_CATEGORIES
        and signal.signal_type in _DOMINANT_SUMMARY_REASON_KEYS
        and _signal_penalty(signal) > 0
    ]
    if not eligible:
        return None
    return max(eligible, key=_signal_penalty)


def risk_level_for_score(score: float) -> RiskLevel:
    if score >= 81:
        return RiskLevel.SAFE
    if score >= 61:
        return RiskLevel.LOW
    if score >= 41:
        return RiskLevel.MEDIUM
    if score >= 21:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def verdict_for_level(risk_level: RiskLevel) -> VerdictType:
    if risk_level is RiskLevel.SAFE:
        return VerdictType.TRUSTED
    if risk_level is RiskLevel.LOW:
        return VerdictType.CAUTION
    if risk_level is RiskLevel.MEDIUM:
        return VerdictType.SUSPICIOUS
    return VerdictType.LIKELY_MALICIOUS


def _is_terminal_blacklist(signals: list[AnalysisSignal]) -> bool:
    return any(
        signal.signal_type is SignalType.BLACKLIST_MATCH
        and signal.confidence.as_ratio >= 0.98
        for signal in signals
    )


def _top_signal_titles(
    signals: list[AnalysisSignal], max_items: int = 5
) -> tuple[str, ...]:
    sorted_signals = sorted(signals, key=_signal_penalty, reverse=True)
    return tuple(signal.title for signal in sorted_signals[:max_items])


def _top_signal_titles_from_penalties(
    penalties: list[tuple[str, float]],
    max_items: int = 5,
) -> tuple[str, ...]:
    ranked = sorted(penalties, key=lambda item: item[1], reverse=True)
    return tuple(item[0] for item in ranked[:max_items])
