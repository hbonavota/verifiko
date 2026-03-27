import re
from dataclasses import dataclass

from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupError,
    InfrastructureLookupPort,
)
from app.application.ports.redirect_resolver import RedirectResolution
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.message_resolver import build_localized_signal, evidence_ref, resolve_message
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

_SENSITIVE_TERMS = {
    "account",
    "bank",
    "billing",
    "confirm",
    "login",
    "mail",
    "microsoft",
    "office365",
    "outlook",
    "password",
    "paypal",
    "secure",
    "signin",
    "update",
    "verify",
    "wallet",
    "webmail",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DYNAMIC_DNS_SUFFIXES = (
    ".duckdns.org",
    ".dynu.net",
    ".dyndns.org",
    ".dynv6.net",
    ".hopto.org",
    ".myftp.org",
    ".no-ip.org",
    ".no-ip.biz",
    ".serveftp.com",
    ".servehttp.com",
    ".sytes.net",
    ".zapto.org",
)
_RESIDENTIAL_PTR_TOKENS = {
    "broadband",
    "cust",
    "customer",
    "dial",
    "dsl",
    "dyn",
    "dynamic",
    "fiber",
    "pool",
    "pppoe",
    "res",
    "residential",
    "subs",
}
_KNOWN_BENIGN_PTR_HINTS = (
    ".akamaitechnologies.com",
    ".akamaiedge.net",
    ".cloudflare.com",
    ".edgekey.net",
    ".edgesuite.net",
    ".fastly.net",
)


@dataclass(slots=True)
class InfrastructureSignalAnalyzer:
    infrastructure_lookup: InfrastructureLookupPort
    source: str = "infrastructure-intelligence-analyzer"

    def analyze_with_context(
        self,
        normalized_url: NormalizedUrl,
        redirect_resolution: RedirectResolution | None = None,
    ) -> SignalAnalysisResult:
        effective_target = self._effective_target(normalized_url, redirect_resolution)
        try:
            profile = self.infrastructure_lookup.lookup(
                effective_target.ascii_host,
                effective_target.port or (443 if effective_target.scheme == "https" else 80),
            )
        except InfrastructureLookupError:
            return SignalAnalysisResult(
                warnings=(resolve_message("warning.infrastructure_unavailable"),)
            )

        matched_patterns = self._matched_patterns(profile)
        if not matched_patterns:
            return SignalAnalysisResult()

        sensitive_terms = self._sensitive_terms(effective_target)
        severity = SignalSeverity.HIGH if sensitive_terms else SignalSeverity.MEDIUM
        confidence = min(
            91,
            68 + len(matched_patterns) * 8 + (6 if sensitive_terms else 0),
        )
        evidence = [
            evidence_ref("evidence.effective_target_host", host=effective_target.ascii_host),
            evidence_ref(
                "evidence.infrastructure_provider",
                provider_name=profile.provider_name,
            ),
            evidence_ref(
                "evidence.resolved_addresses",
                addresses=", ".join(address.ip_address for address in profile.resolved_addresses[:3]),
            ),
            evidence_ref(
                "evidence.matched_infrastructure_patterns",
                patterns=", ".join(matched_patterns),
            ),
        ]
        reverse_samples = [
            address.reverse_hostname
            for address in profile.resolved_addresses
            if address.reverse_hostname
        ]
        if reverse_samples:
            evidence.append(
                evidence_ref("evidence.reverse_dns_sample", reverse_hostname=reverse_samples[0])
            )
        if sensitive_terms:
            evidence.append(
                evidence_ref(
                    "evidence.matched_sensitive_url_terms",
                    terms=", ".join(sensitive_terms[:4]),
                )
            )
        if redirect_resolution is not None and redirect_resolution.hops:
            evidence.append(
                evidence_ref(
                    "evidence.effective_target_derived_from_redirect_chain",
                    final_url=redirect_resolution.final_url,
                )
            )

        return SignalAnalysisResult(
            signals=(
                build_localized_signal(
                    signal_type=SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN,
                    category=SIGNAL_CATEGORY_MAP[SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN],
                    severity=severity,
                    confidence=ConfidenceScore(confidence),
                    source=self.source,
                    base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN],
                    message_key="signal.suspicious_infrastructure_pattern",
                    message_params={"evidence": evidence},
                    tags=("infrastructure", *matched_patterns[:3]),
                ),
            )
        )

    def _effective_target(
        self,
        normalized_url: NormalizedUrl,
        redirect_resolution: RedirectResolution | None,
    ) -> NormalizedUrl:
        if redirect_resolution is None or not redirect_resolution.hops:
            return normalized_url
        return NormalizedUrl.from_raw(redirect_resolution.final_url)

    def _matched_patterns(self, profile) -> list[str]:
        matches: set[str] = set()
        for address in profile.resolved_addresses:
            reverse_hostname = (address.reverse_hostname or "").lower().rstrip(".")
            if not reverse_hostname:
                continue
            if reverse_hostname.endswith(_KNOWN_BENIGN_PTR_HINTS):
                continue
            if reverse_hostname.endswith(_DYNAMIC_DNS_SUFFIXES):
                matches.add("dynamic-dns")
            reverse_tokens = {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(reverse_hostname)}
            if reverse_tokens.intersection(_RESIDENTIAL_PTR_TOKENS):
                matches.add("residential-ptr")
        return sorted(matches)

    def _sensitive_terms(self, normalized_url: NormalizedUrl) -> list[str]:
        text = " ".join(
            [
                normalized_url.host,
                normalized_url.userinfo.replace(":", " "),
                normalized_url.decoded_path.replace("/", " "),
                normalized_url.decoded_query.replace("&", " "),
                normalized_url.decoded_fragment.replace("/", " "),
            ]
        )
        tokens = {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)}
        return sorted(_SENSITIVE_TERMS.intersection(tokens))
