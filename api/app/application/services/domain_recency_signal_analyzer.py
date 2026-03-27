from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationLookupError,
)
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.message_resolver import build_localized_signal, evidence_ref, resolve_message
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

EXTREME_RECENCY_THRESHOLD_DAYS = 7
RECENT_RECENCY_THRESHOLD_DAYS = 30


@dataclass(slots=True)
class DomainRecencySignalAnalyzer:
    domain_age_lookup: DomainAgeLookupPort
    source: str = "domain-recency-analyzer"
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def analyze(self, normalized_url: NormalizedUrl) -> list[AnalysisSignal]:
        return list(self.analyze_with_context(normalized_url).signals)

    def analyze_with_context(self, normalized_url: NormalizedUrl) -> SignalAnalysisResult:
        if normalized_url.is_ip_address:
            return SignalAnalysisResult()

        try:
            registration = self.domain_age_lookup.lookup(normalized_url.registered_domain)
        except DomainRegistrationLookupError:
            return SignalAnalysisResult(
                warnings=(resolve_message("warning.domain_registration_unavailable"),)
            )

        if registration is None:
            return SignalAnalysisResult()

        age_in_days = self._age_in_days(registration.registered_at)
        if age_in_days < 0:
            return SignalAnalysisResult()

        if age_in_days <= EXTREME_RECENCY_THRESHOLD_DAYS:
            return SignalAnalysisResult(
                signals=(
                    self._signal(
                        severity=SignalSeverity.HIGH,
                        confidence=93,
                        message_key="signal.very_recent_domain_registration",
                        threshold_days=EXTREME_RECENCY_THRESHOLD_DAYS,
                        observed_domain=normalized_url.registered_domain,
                        registered_at=registration.registered_at,
                        age_in_days=age_in_days,
                        provider_name=registration.provider_name,
                    ),
                ),
            )

        if age_in_days <= RECENT_RECENCY_THRESHOLD_DAYS:
            return SignalAnalysisResult(
                signals=(
                    self._signal(
                        severity=SignalSeverity.MEDIUM,
                        confidence=81,
                        message_key="signal.recent_domain_registration",
                        threshold_days=RECENT_RECENCY_THRESHOLD_DAYS,
                        observed_domain=normalized_url.registered_domain,
                        registered_at=registration.registered_at,
                        age_in_days=age_in_days,
                        provider_name=registration.provider_name,
                    ),
                ),
            )

        return SignalAnalysisResult()

    def _age_in_days(self, registered_at: datetime) -> int:
        reference_time = self.current_time_provider()
        normalized_registered_at = registered_at.astimezone(timezone.utc)
        normalized_reference_time = reference_time.astimezone(timezone.utc)
        return (normalized_reference_time.date() - normalized_registered_at.date()).days

    def _signal(
        self,
        severity: SignalSeverity,
        confidence: float,
        message_key: str,
        threshold_days: int,
        observed_domain: str,
        registered_at: datetime,
        age_in_days: int,
        provider_name: str,
    ) -> AnalysisSignal:
        return build_localized_signal(
            signal_type=SignalType.RECENT_DOMAIN_REGISTRATION,
            category=SIGNAL_CATEGORY_MAP[SignalType.RECENT_DOMAIN_REGISTRATION],
            severity=severity,
            confidence=ConfidenceScore(confidence),
            source=self.source,
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.RECENT_DOMAIN_REGISTRATION],
            message_key=message_key,
            message_params={
                "threshold_days": threshold_days,
                "evidence": [
                    evidence_ref("evidence.observed_domain", observed_domain=observed_domain),
                    evidence_ref(
                        "evidence.registration_date",
                        registration_date=registered_at.astimezone(timezone.utc).date().isoformat(),
                    ),
                    evidence_ref("evidence.computed_domain_age_days", age_in_days=age_in_days),
                    evidence_ref("evidence.lookup_provider", provider_name=provider_name),
                ],
            },
            tags=("domain-age", "registration-recency"),
        )
