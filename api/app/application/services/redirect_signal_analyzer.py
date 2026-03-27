from dataclasses import dataclass
import re

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

_INTERSTITIAL_REDIRECT_TOKENS = {"continue", "out", "away", "redirect", "redirecionamento"}
_PHISHING_LURE_TOKENS = {
    "account",
    "auth",
    "billing",
    "confirm",
    "fine",
    "invoice",
    "login",
    "notice",
    "password",
    "payment",
    "penalty",
    "secure",
    "signin",
    "ticket",
    "toll",
    "traffic",
    "unlock",
    "update",
    "validate",
    "verify",
    "violation",
    "wallet",
    "webmail",
}
_SHORTENER_DOMAINS = {
    "amzn.to",
    "bit.ly",
    "cutt.ly",
    "g.co",
    "goo.gl",
    "is.gd",
    "lnkd.in",
    "ow.ly",
    "rebrand.ly",
    "rb.gy",
    "t.co",
    "tinyurl.com",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


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
        clean_single_hop_redirect = self._is_clean_single_hop_redirect(
            normalized_url=normalized_url,
            resolved_final=resolved_final,
            resolution=resolution,
            domain_crossings=domain_crossings,
            distinct_hosts=distinct_hosts,
            scheme_downgrade=scheme_downgrade,
        )
        suspicious_chain = (
            scheme_downgrade
            or len(domain_crossings) >= 2
            or len(distinct_hosts) >= 3
            or (
                resolved_final.registered_domain != normalized_url.registered_domain
                and not clean_single_hop_redirect
            )
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

        strong_redirect_cues = (
            len(resolution.hops) >= 2
            or len(domain_crossings) >= 2
            or len(distinct_hosts) >= 3
            or scheme_downgrade
            or self._has_phishing_like_final_cues(resolved_final)
        )
        severity = SignalSeverity.HIGH if strong_redirect_cues else SignalSeverity.MEDIUM
        if strong_redirect_cues:
            confidence = min(94, 72 + len(resolution.hops) * 6 + len(domain_crossings) * 7)
        else:
            confidence = min(82, 64 + len(domain_crossings) * 6)

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

    def _is_clean_single_hop_redirect(
        self,
        normalized_url: NormalizedUrl,
        resolved_final: NormalizedUrl,
        resolution: RedirectResolution,
        domain_crossings: list[str],
        distinct_hosts: set[str],
        scheme_downgrade: bool,
    ) -> bool:
        if len(resolution.hops) != 1 or scheme_downgrade:
            return False
        if len(domain_crossings) != 1 or len(distinct_hosts) > 2:
            return False
        if self._has_phishing_like_final_cues(resolved_final):
            return False
        final_tokens = self._text_tokens(resolved_final)
        if _INTERSTITIAL_REDIRECT_TOKENS.intersection(final_tokens):
            return True
        return normalized_url.registered_domain in _SHORTENER_DOMAINS

    def _has_phishing_like_final_cues(self, resolved_final: NormalizedUrl) -> bool:
        return bool(_PHISHING_LURE_TOKENS.intersection(self._text_tokens(resolved_final)))

    def _text_tokens(self, normalized_url: NormalizedUrl) -> set[str]:
        combined = " ".join(
            [
                normalized_url.host,
                normalized_url.decoded_path.replace("/", " "),
                normalized_url.decoded_query.replace("&", " "),
                normalized_url.decoded_fragment.replace("/", " "),
            ]
        ).lower()
        return {match.group(0) for match in _TOKEN_PATTERN.finditer(combined)}
