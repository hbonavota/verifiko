from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationLookupError,
)
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
        if normalized_url.is_ip_address:
            return []

        try:
            registration = self.domain_age_lookup.lookup(normalized_url.registered_domain)
        except DomainRegistrationLookupError:
            return []

        if registration is None:
            return []

        age_in_days = self._age_in_days(registration.registered_at)
        if age_in_days < 0:
            return []

        if age_in_days <= EXTREME_RECENCY_THRESHOLD_DAYS:
            return [
                self._signal(
                    severity=SignalSeverity.HIGH,
                    confidence=93,
                    title="Very recent domain registration",
                    description=(
                        "The registered domain appears to have been created within the last "
                        f"{EXTREME_RECENCY_THRESHOLD_DAYS} days."
                    ),
                    observed_domain=normalized_url.registered_domain,
                    registered_at=registration.registered_at,
                    age_in_days=age_in_days,
                    provider_name=registration.provider_name,
                )
            ]

        if age_in_days <= RECENT_RECENCY_THRESHOLD_DAYS:
            return [
                self._signal(
                    severity=SignalSeverity.MEDIUM,
                    confidence=81,
                    title="Recent domain registration",
                    description=(
                        "The registered domain appears to have been created within the last "
                        f"{RECENT_RECENCY_THRESHOLD_DAYS} days."
                    ),
                    observed_domain=normalized_url.registered_domain,
                    registered_at=registration.registered_at,
                    age_in_days=age_in_days,
                    provider_name=registration.provider_name,
                )
            ]

        return []

    def _age_in_days(self, registered_at: datetime) -> int:
        reference_time = self.current_time_provider()
        normalized_registered_at = registered_at.astimezone(timezone.utc)
        normalized_reference_time = reference_time.astimezone(timezone.utc)
        return (normalized_reference_time.date() - normalized_registered_at.date()).days

    def _signal(
        self,
        severity: SignalSeverity,
        confidence: float,
        title: str,
        description: str,
        observed_domain: str,
        registered_at: datetime,
        age_in_days: int,
        provider_name: str,
    ) -> AnalysisSignal:
        return AnalysisSignal.create(
            signal_type=SignalType.RECENT_DOMAIN_REGISTRATION,
            category=SIGNAL_CATEGORY_MAP[SignalType.RECENT_DOMAIN_REGISTRATION],
            severity=severity,
            confidence=ConfidenceScore(confidence),
            title=title,
            description=description,
            source=self.source,
            base_weight=BASE_SIGNAL_WEIGHTS[SignalType.RECENT_DOMAIN_REGISTRATION],
            evidence=(
                f"Observed domain: {observed_domain}.",
                f"Registration date: {registered_at.astimezone(timezone.utc).date().isoformat()}.",
                f"Computed domain age: {age_in_days} day(s).",
                f"Lookup provider: {provider_name}.",
            ),
            tags=("domain-age", "registration-recency"),
        )
