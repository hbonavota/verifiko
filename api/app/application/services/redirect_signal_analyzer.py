import re
from dataclasses import dataclass

from app.application.ports.redirect_resolver import (
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.message_resolver import (
    build_localized_signal,
    evidence_ref,
    resolve_message,
)
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import (
    BASE_SIGNAL_WEIGHTS,
    SIGNAL_CATEGORY_MAP,
)
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

_INTERSTITIAL_REDIRECT_TOKENS = {
    "continue",
    "out",
    "away",
    "redirect",
    "redirecionamento",
}
_PHISHING_LURE_TOKENS = {
    "account",
    "auth",
    "billing",
    "challenge",
    "confirm",
    "fine",
    "invoice",
    "login",
    "mfa",
    "notice",
    "otp",
    "password",
    "payment",
    "penalty",
    "reauth",
    "reset",
    "recovery",
    "secure",
    "signin",
    "ticket",
    "toll",
    "traffic",
    "unlock",
    "update",
    "validate",
    "verify",
    "verification",
    "violation",
    "wallet",
    "webmail",
}
_CONTEXTUAL_ATO_LURE_TOKENS = {"session"}
_CONTEXTUAL_ATO_SUPPORT_TOKENS = {
    "account",
    "auth",
    "mail",
    "office365",
    "outlook",
    "password",
    "secure",
    "security",
    "verify",
    "verification",
    "webmail",
}
_CONTEXTUAL_APPROVE_LURE_TOKENS = {"approve"}
_CONTEXTUAL_APPROVE_SUPPORT_TOKENS = {
    "amazon",
    "apple",
    "appleid",
    "dropbox",
    "facebook",
    "google",
    "mail",
    "mailbox",
    "microsoft",
    "office365",
    "onedrive",
    "outlook",
    "paypal",
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
_QUESTIONABLE_DESTINATION_TLDS = {
    "buzz",
    "click",
    "gq",
    "info",
    "link",
    "live",
    "rest",
    "shop",
    "top",
    "xyz",
}
_OFFICIAL_AUTH_DOMAINS = {
    "apple.com",
    "dropbox.com",
    "github.com",
    "google.com",
    "live.com",
    "microsoftonline.com",
    "paypal.com",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(slots=True)
class RedirectSignalAnalyzer:
    redirect_resolver: RedirectResolverPort
    source: str = "redirect-chain-analyzer"

    def analyze_with_context(
        self, normalized_url: NormalizedUrl
    ) -> SignalAnalysisResult:
        try:
            resolution = self.redirect_resolver.resolve(normalized_url.normalized)
        except RedirectResolutionError:
            return SignalAnalysisResult(
                warnings=(resolve_message("warning.redirect_resolution_unavailable"),)
            )

        if not resolution.hops:
            return SignalAnalysisResult(redirect_resolution=resolution)

        resolved_final = NormalizedUrl.from_raw(resolution.final_url)
        domain_crossings = self._domain_crossings(normalized_url, resolution)
        distinct_hosts = {resolved_final.ascii_host}
        distinct_hosts.update(
            NormalizedUrl.from_raw(hop.target_url).ascii_host for hop in resolution.hops
        )
        scheme_downgrade = (
            normalized_url.scheme == "https" and resolved_final.scheme == "http"
        )
        questionable_destination_structure = (
            self._has_questionable_destination_structure(resolved_final)
        )
        clean_single_hop_redirect = self._is_clean_single_hop_redirect(
            normalized_url=normalized_url,
            resolved_final=resolved_final,
            resolution=resolution,
            domain_crossings=domain_crossings,
            distinct_hosts=distinct_hosts,
            scheme_downgrade=scheme_downgrade,
            questionable_destination_structure=questionable_destination_structure,
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
                "Redirect chain crossed registered domains: "
                f"{', '.join(domain_crossings[:3])}."
            )

        if scheme_downgrade:
            evidence.append("Redirect chain downgraded transport from HTTPS to HTTP.")
        if questionable_destination_structure:
            evidence.append(
                resolve_message(
                    "evidence.final_destination_uses_questionable_tld",
                    {"tld": self._registered_tld(resolved_final)},
                )
            )

        strong_redirect_cues = (
            len(resolution.hops) >= 2
            or len(domain_crossings) >= 2
            or len(distinct_hosts) >= 3
            or scheme_downgrade
            or questionable_destination_structure
            or self._has_phishing_like_final_cues(resolved_final)
        )
        severity = (
            SignalSeverity.HIGH if strong_redirect_cues else SignalSeverity.MEDIUM
        )
        if strong_redirect_cues:
            confidence = min(
                94, 72 + len(resolution.hops) * 6 + len(domain_crossings) * 7
            )
        else:
            confidence = min(82, 64 + len(domain_crossings) * 6)

        signals = [
            build_localized_signal(
                signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
                category=SIGNAL_CATEGORY_MAP[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
                severity=severity,
                confidence=ConfidenceScore(confidence),
                source=self.source,
                base_weight=BASE_SIGNAL_WEIGHTS[SignalType.SUSPICIOUS_REDIRECT_CHAIN],
                message_key="signal.observed_redirect_chain",
                message_params={
                    "evidence": _build_redirect_evidence_refs(
                        hop_count=len(resolution.hops),
                        final_url=resolution.final_url,
                        provider_name=resolution.provider_name,
                        domain_crossings=domain_crossings,
                        scheme_downgrade=scheme_downgrade,
                        questionable_destination_tld=(
                            self._registered_tld(resolved_final)
                            if questionable_destination_structure
                            else None
                        ),
                    ),
                },
                tags=("redirect-chain", resolved_final.registered_domain),
            )
        ]
        if questionable_destination_structure:
            signals.append(
                build_localized_signal(
                    signal_type=SignalType.QUESTIONABLE_DESTINATION_TLD,
                    category=SIGNAL_CATEGORY_MAP[
                        SignalType.QUESTIONABLE_DESTINATION_TLD
                    ],
                    severity=SignalSeverity.MEDIUM,
                    confidence=ConfidenceScore(84),
                    source=self.source,
                    base_weight=BASE_SIGNAL_WEIGHTS[
                        SignalType.QUESTIONABLE_DESTINATION_TLD
                    ],
                    message_key="signal.questionable_destination_tld_after_redirect",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.final_destination_uses_questionable_tld",
                                tld=self._registered_tld(resolved_final),
                            ),
                            evidence_ref(
                                "evidence.final_url_after_redirects",
                                final_url=resolution.final_url,
                            ),
                        ]
                    },
                    tags=(
                        "redirect-chain",
                        "questionable-tld",
                        resolved_final.registered_domain,
                    ),
                )
            )

        return SignalAnalysisResult(
            signals=tuple(signals),
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
        questionable_destination_structure: bool,
    ) -> bool:
        if len(resolution.hops) != 1 or scheme_downgrade:
            return False
        if len(domain_crossings) != 1 or len(distinct_hosts) > 2:
            return False
        if self._has_phishing_like_final_cues(resolved_final):
            return False
        if questionable_destination_structure:
            return False
        final_tokens = self._text_tokens(resolved_final)
        if _INTERSTITIAL_REDIRECT_TOKENS.intersection(final_tokens):
            return True
        return normalized_url.registered_domain in _SHORTENER_DOMAINS

    def _has_phishing_like_final_cues(self, resolved_final: NormalizedUrl) -> bool:
        if self._is_official_auth_destination(resolved_final):
            return False

        tokens = self._text_tokens(resolved_final)
        if _PHISHING_LURE_TOKENS.intersection(tokens):
            return True

        if bool(_CONTEXTUAL_ATO_LURE_TOKENS.intersection(tokens)) and bool(
            _CONTEXTUAL_ATO_SUPPORT_TOKENS.intersection(tokens)
        ):
            return True

        return bool(_CONTEXTUAL_APPROVE_LURE_TOKENS.intersection(tokens)) and bool(
            _CONTEXTUAL_APPROVE_SUPPORT_TOKENS.intersection(tokens)
        )

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

    def _has_questionable_destination_structure(
        self, normalized_url: NormalizedUrl
    ) -> bool:
        return self._registered_tld(normalized_url) in _QUESTIONABLE_DESTINATION_TLDS

    def _registered_tld(self, normalized_url: NormalizedUrl) -> str:
        labels = [
            label for label in normalized_url.registered_domain.split(".") if label
        ]
        return labels[-1].lower() if len(labels) >= 2 else ""

    def _is_official_auth_destination(self, normalized_url: NormalizedUrl) -> bool:
        return normalized_url.registered_domain in _OFFICIAL_AUTH_DOMAINS


def _build_redirect_evidence_refs(
    hop_count: int,
    final_url: str,
    provider_name: str,
    domain_crossings: list[str],
    scheme_downgrade: bool,
    questionable_destination_tld: str | None,
) -> list[dict[str, object]]:
    evidence = [
        evidence_ref("evidence.redirect_hops_observed", hop_count=hop_count),
        evidence_ref("evidence.final_url_after_redirects", final_url=final_url),
        evidence_ref("evidence.redirect_resolver", provider_name=provider_name),
    ]
    if domain_crossings:
        evidence.append(
            evidence_ref(
                "evidence.redirect_chain_crossed_registered_domains",
                crossings=", ".join(domain_crossings[:3]),
            )
        )
    if scheme_downgrade:
        evidence.append(evidence_ref("evidence.redirect_chain_downgraded_transport"))
    if questionable_destination_tld:
        evidence.append(
            evidence_ref(
                "evidence.final_destination_uses_questionable_tld",
                tld=questionable_destination_tld,
            )
        )
    return evidence
