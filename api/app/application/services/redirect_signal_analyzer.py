from dataclasses import dataclass

from app.application.ports.redirect_resolver import (
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.application.services.analysis_result import SignalAnalysisResult
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl


@dataclass(slots=True)
class RedirectSignalAnalyzer:
    redirect_resolver: RedirectResolverPort
    source: str = "redirect-chain-analyzer"

    def analyze_with_context(self, normalized_url: NormalizedUrl) -> SignalAnalysisResult:
        try:
            resolution = self.redirect_resolver.resolve(normalized_url.normalized)
        except RedirectResolutionError:
            return SignalAnalysisResult(
                warnings=("Redirect resolution could not be completed for this run.",)
            )

        if not resolution.hops:
            return SignalAnalysisResult(redirect_resolution=resolution)

        resolved_final = NormalizedUrl.from_raw(resolution.final_url)
        domain_crossings = self._domain_crossings(normalized_url, resolution)
        distinct_hosts = {resolved_final.ascii_host}
        distinct_hosts.update(
            NormalizedUrl.from_raw(hop.target_url).ascii_host for hop in resolution.hops
        )
        scheme_downgrade = normalized_url.scheme == "https" and resolved_final.scheme == "http"
        suspicious_chain = (
            resolved_final.registered_domain != normalized_url.registered_domain
            or len(domain_crossings) >= 1
            or len(distinct_hosts) >= 3
            or scheme_downgrade
        )

        if not suspicious_chain:
            return SignalAnalysisResult(redirect_resolution=resolution)

        evidence = [
            f"Redirect hops observed: {len(resolution.hops)}.",
            f"Final URL after redirects: {resolution.final_url}.",
            f"Redirect resolver: {resolution.provider_name}.",
        ]
        if domain_crossings:
            evidence.append(
                f"Redirect chain crossed registered domains: {', '.join(domain_crossings[:3])}."
            )

        if scheme_downgrade:
            evidence.append("Redirect chain downgraded transport from HTTPS to HTTP.")

        severity = SignalSeverity.HIGH
        confidence = min(94, 72 + len(resolution.hops) * 6 + len(domain_crossings) * 7)

        return SignalAnalysisResult(
            signals=(
                AnalysisSignal.create(
                    signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
                    category=SIGNAL_CATEGORY_MAP[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
                    severity=severity,
                    confidence=ConfidenceScore(confidence),
                    title="Observed redirect chain",
                    description=(
                        "The submitted URL resolved through one or more redirects before reaching "
                        "its final destination."
                    ),
                    source=self.source,
                    base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
                    evidence=tuple(evidence),
                    tags=("redirect-chain", resolved_final.registered_domain),
                ),
            ),
            redirect_resolution=resolution,
        )

    def _domain_crossings(
        self,
        normalized_url: NormalizedUrl,
        resolution: RedirectResolution,
    ) -> list[str]:
        current_domain = normalized_url.registered_domain
        crossings: list[str] = []
        for hop in resolution.hops:
            target_domain = NormalizedUrl.from_raw(hop.target_url).registered_domain
            if target_domain != current_domain:
                crossings.append(f"{current_domain} -> {target_domain}")
                current_domain = target_domain
        return crossings
