from dataclasses import dataclass
from dataclasses import replace

from app.application.ports.redirect_resolver import RedirectResolution
from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)
from app.application.services.analysis_result import SignalAnalysisResult
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl


@dataclass(slots=True)
class ReputationSignalAnalyzer:
    reputation_lookup: ReputationLookupPort
    source: str = "reputation-analyzer"

    def analyze_with_context(
        self,
        normalized_url: NormalizedUrl,
        redirect_resolution: RedirectResolution | None = None,
    ) -> SignalAnalysisResult:
        warnings: list[str] = []
        candidates = self._candidate_hosts(normalized_url, redirect_resolution)
        matches: list[ReputationMatch] = []

        for candidate_value, candidate_scope in candidates:
            try:
                match = self.reputation_lookup.lookup(candidate_value)
            except ReputationLookupError:
                warnings.append("Blacklist reputation intelligence was unavailable for this run.")
                continue

            if match is not None:
                matches.append(
                    replace(
                        match,
                        queried_value=candidate_value,
                        match_scope=candidate_scope,
                    )
                )

        if not matches:
            return SignalAnalysisResult(warnings=tuple(dict.fromkeys(warnings)))

        strongest_match = max(matches, key=lambda item: item.confidence)
        severity = (
            SignalSeverity.CRITICAL
            if strongest_match.match_scope in {"host", "redirect_host"}
            else SignalSeverity.HIGH
        )
        confidence = strongest_match.confidence
        evidence = [
            f"Listed value: {strongest_match.queried_value}.",
            f"Reputation provider: {strongest_match.provider_name}.",
            f"Provider references: {strongest_match.reference_count}.",
            strongest_match.description,
        ]
        if redirect_resolution is not None and redirect_resolution.hops:
            evidence.append(f"Final redirect target: {redirect_resolution.final_url}.")

        return SignalAnalysisResult(
            signals=(
                AnalysisSignal.create(
                    signal_type=SignalType.BLACKLIST_MATCH,
                    category=SIGNAL_CATEGORY_MAP[SignalType.BLACKLIST_MATCH],
                    severity=severity,
                    confidence=ConfidenceScore(confidence),
                    title="Reputation blacklist match",
                    description=(
                        "The target or a resolved redirect destination matched external malicious "
                        "URL reputation intelligence."
                    ),
                    source=self.source,
                    base_weight=BASE_SIGNAL_WEIGHTS[SignalType.BLACKLIST_MATCH],
                    evidence=tuple(evidence),
                    tags=("reputation", strongest_match.match_scope),
                ),
            ),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _candidate_hosts(
        self,
        normalized_url: NormalizedUrl,
        redirect_resolution: RedirectResolution | None,
    ) -> tuple[tuple[str, str], ...]:
        values = [
            (normalized_url.ascii_host, "host"),
            (normalized_url.registered_domain, "registered_domain"),
        ]
        if redirect_resolution is not None:
            final_target = NormalizedUrl.from_raw(redirect_resolution.final_url)
            values.extend(
                [
                    (final_target.ascii_host, "redirect_host"),
                    (final_target.registered_domain, "redirect_registered_domain"),
                ]
            )

        ordered = []
        seen = set()
        for value, scope in values:
            if value and value not in seen:
                seen.add(value)
                ordered.append((value, scope))
        return tuple(ordered)
