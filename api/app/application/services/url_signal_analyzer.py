import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl

from app.application.services.message_resolver import build_localized_signal, evidence_ref
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

_SUSPICIOUS_KEYWORDS = {
    "account",
    "auth",
    "billing",
    "confirm",
    "invoice",
    "login",
    "password",
    "payroll",
    "recover",
    "reset",
    "secure",
    "signin",
    "unlock",
    "update",
    "validate",
    "verify",
    "wallet",
    "webmail",
}
_BRAND_KEYWORDS = {
    "amazon",
    "apple",
    "appleid",
    "bankofamerica",
    "dhl",
    "dropbox",
    "facebook",
    "google",
    "instagram",
    "microsoft",
    "netflix",
    "openai",
    "onedrive",
    "outlook",
    "paypal",
    "hmrc",
    "irs",
    "ssa",
    "usps",
}
_EMAIL_LURE_KEYWORDS = {"mail", "mailbox", "office365", "outlook", "webmail"}
_INSTITUTION_CONTEXT_KEYWORDS = {
    "authority",
    "customs",
    "dgt",
    "government",
    "hmrc",
    "irs",
    "revenue",
    "ssa",
    "traffic",
    "trafico",
    "usps",
}
_INSTITUTION_DEMAND_KEYWORDS = {
    "appeal",
    "fine",
    "notice",
    "pay",
    "payment",
    "penalty",
    "settle",
    "ticket",
    "toll",
    "violation",
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
_REPUTABLE_REGISTERED_DOMAINS = {
    "github.com",
    "google.com",
    "mozilla.org",
    "openai.com",
    "python.org",
}
_UNCOMMON_BRANDISH_TLDS = {"buzz", "click", "gq", "info", "link", "live", "rest", "shop", "top", "xyz"}
_COMMON_DOMAIN_SUFFIXES = {"ac", "app", "biz", "co", "com", "dev", "edu", "gov", "info", "io", "net", "org"}
_OFFICIAL_INSTITUTION_SUFFIXES = (".gov", ".gov.uk", ".gob.es", ".gov.es", ".gc.ca")
_REDIRECT_KEYS = {"continue", "next", "redirect", "return", "target", "url"}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_GENERIC_AUTH_KEYWORDS = {"account", "auth", "login", "secure", "signin", "verify"}


@dataclass(slots=True)
class DeterministicUrlSignalAnalyzer:
    source: str = "url-rule-analyzer"

    def analyze(self, normalized_url: NormalizedUrl) -> list[AnalysisSignal]:
        signals: list[AnalysisSignal] = []
        host_labels = [label for label in normalized_url.ascii_host.split(".") if label]
        subdomain_labels = [label for label in normalized_url.subdomain.split(".") if label]
        text_tokens = _tokenize(
            " ".join(
                [
                    normalized_url.host,
                    normalized_url.userinfo.replace(":", " "),
                    normalized_url.decoded_path.replace("/", " "),
                    normalized_url.decoded_query.replace("&", " "),
                    normalized_url.decoded_fragment.replace("/", " "),
                ]
            )
        )
        keyword_matches = sorted(_SUSPICIOUS_KEYWORDS.intersection(text_tokens))
        brand_matches = sorted(_BRAND_KEYWORDS.intersection(text_tokens))
        institution_context_matches = sorted(_INSTITUTION_CONTEXT_KEYWORDS.intersection(text_tokens))
        institution_demand_matches = sorted(_INSTITUTION_DEMAND_KEYWORDS.intersection(text_tokens))
        deceptive_brand_pattern = self._deceptive_brand_subdomain_pattern(subdomain_labels)
        tld = host_labels[-1] if len(host_labels) >= 2 else ""

        if normalized_url.is_ip_address:
            signals.append(
                self._signal(
                    signal_type=SignalType.IP_ADDRESS_URL,
                    severity=SignalSeverity.HIGH,
                    confidence=96,
                    message_key="signal.direct_ip_address_target",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.host_resolves_to_raw_ip",
                                ascii_host=normalized_url.ascii_host,
                            )
                        ]
                    },
                    tags=("ip-host", "domain-structure"),
                )
            )

        if normalized_url.contains_unicode or normalized_url.contains_punycode:
            evidence = []
            if normalized_url.contains_unicode:
                evidence.append(
                    evidence_ref("evidence.rendered_host", host=normalized_url.host)
                )
            if normalized_url.contains_punycode:
                evidence.append(
                    evidence_ref(
                        "evidence.ascii_host_contains_punycode_labels",
                        ascii_host=normalized_url.ascii_host,
                    )
                )
            else:
                evidence.append(
                    evidence_ref("evidence.ascii_host", ascii_host=normalized_url.ascii_host)
                )

            signals.append(
                self._signal(
                    signal_type=SignalType.UNICODE_HOMOGRAPH,
                    severity=SignalSeverity.HIGH,
                    confidence=88 if normalized_url.contains_unicode else 84,
                    message_key="signal.unicode_or_punycode_hostname_pattern",
                    message_params={"evidence": list(evidence)},
                    tags=("unicode-host", "homograph-review"),
                )
            )

        if normalized_url.contains_zero_width_chars:
            signals.append(
                self._signal(
                    signal_type=SignalType.ZERO_WIDTH_CHAR_INJECTION,
                    severity=SignalSeverity.CRITICAL,
                    confidence=99,
                    message_key="signal.invisible_hostname_characters",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.host_contains_zero_width_characters",
                                host=normalized_url.host,
                            )
                        ]
                    },
                    tags=("zero-width", "hostname-obfuscation"),
                )
            )

        if normalized_url.port is not None and normalized_url.port not in {80, 443}:
            signals.append(
                self._signal(
                    signal_type=SignalType.NON_STANDARD_PORT_USAGE,
                    severity=SignalSeverity.MEDIUM,
                    confidence=74,
                    message_key="signal.non_standard_port_usage",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.observed_explicit_port",
                                port=normalized_url.port,
                            )
                        ]
                    },
                    tags=("port", "network-transport"),
                )
            )

        if normalized_url.registered_domain in _SHORTENER_DOMAINS:
            signals.append(
                self._signal(
                    signal_type=SignalType.SHORTENED_URL,
                    severity=SignalSeverity.MEDIUM,
                    confidence=82,
                    message_key="signal.shortened_destination",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.registered_domain_is_shortener",
                                registered_domain=normalized_url.registered_domain,
                            )
                        ]
                    },
                    tags=("shortener", "navigation"),
                )
            )

        redirect_indicators = self._redirect_indicators(normalized_url)
        if redirect_indicators:
            signals.append(
                self._signal(
                    signal_type=SignalType.SUSPICIOUS_REDIRECT_CHAIN,
                    severity=SignalSeverity.MEDIUM,
                    confidence=min(90, 68 + len(redirect_indicators) * 6),
                    message_key="signal.redirect_style_parameters",
                    message_params={
                        "evidence": list(redirect_indicators),
                    },
                    tags=("redirect", "navigation"),
                )
            )

        if keyword_matches and not self._is_official_auth_flow(normalized_url, keyword_matches):
            keyword_sample = ", ".join(keyword_matches[:4])
            signals.append(
                self._signal(
                    signal_type=SignalType.PHISHING_KEYWORDS,
                    severity=SignalSeverity.HIGH if len(keyword_matches) >= 3 else SignalSeverity.MEDIUM,
                    confidence=min(92, 62 + len(keyword_matches) * 7),
                    message_key="signal.credential_lure_wording_in_url",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.matched_url_keywords",
                                keywords=keyword_sample,
                            )
                        ]
                    },
                    tags=tuple(keyword_matches[:4]),
                )
            )

        if brand_matches and keyword_matches and not self._is_official_brand_target(normalized_url):
            brand_sample = ", ".join(brand_matches[:3])
            signals.append(
                self._signal(
                    signal_type=SignalType.BRAND_IMPERSONATION,
                    severity=SignalSeverity.HIGH,
                    confidence=min(95, 76 + len(brand_matches) * 5 + len(keyword_matches) * 2),
                    message_key="signal.brand_like_impersonation_hints",
                    message_params={
                        "evidence": [
                            evidence_ref("evidence.matched_brand_terms", brands=brand_sample),
                            evidence_ref(
                                "evidence.registered_domain_under_review",
                                registered_domain=normalized_url.registered_domain,
                            ),
                        ]
                    },
                    tags=tuple((brand_matches + keyword_matches)[:5]),
                )
            )
        elif (
            institution_context_matches
            and institution_demand_matches
            and not self._is_official_institution_target(normalized_url)
        ):
            signals.append(
                self._signal(
                    signal_type=SignalType.BRAND_IMPERSONATION,
                    severity=SignalSeverity.HIGH,
                    confidence=min(
                        94,
                        78
                        + len(institution_context_matches) * 5
                        + len(institution_demand_matches) * 4,
                    ),
                    message_key="signal.institution_style_payment_or_penalty_lure",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.matched_institution_terms",
                                terms=", ".join(institution_context_matches[:3]),
                            ),
                            evidence_ref(
                                "evidence.matched_demand_terms",
                                terms=", ".join(institution_demand_matches[:3]),
                            ),
                            evidence_ref(
                                "evidence.registered_domain_under_review",
                                registered_domain=normalized_url.registered_domain,
                            ),
                        ]
                    },
                    tags=tuple((institution_context_matches + institution_demand_matches)[:5]),
                )
            )

        if keyword_matches and _EMAIL_LURE_KEYWORDS.intersection(text_tokens):
            email_terms = sorted(_EMAIL_LURE_KEYWORDS.intersection(text_tokens))
            signals.append(
                self._signal(
                    signal_type=SignalType.TACTICAL_EMAIL_STAGING,
                    severity=SignalSeverity.MEDIUM,
                    confidence=min(90, 72 + len(email_terms) * 6),
                    message_key="signal.mailbox_access_lure_pattern",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.matched_mailbox_terms",
                                terms=", ".join(email_terms),
                            )
                        ]
                    },
                    tags=tuple((email_terms + keyword_matches)[:5]),
                )
            )

        if deceptive_brand_pattern is not None:
            signals.append(
                self._signal(
                    signal_type=SignalType.DECEPTIVE_BRAND_SUBDOMAIN,
                    severity=SignalSeverity.HIGH,
                    confidence=94,
                    message_key="signal.deceptive_brand_in_subdomain_pattern",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.observed_deceptive_fragment",
                                fragment=deceptive_brand_pattern,
                            ),
                            evidence_ref(
                                "evidence.registered_domain_observed",
                                registered_domain=normalized_url.registered_domain,
                            ),
                        ]
                    },
                    tags=("brand-subdomain", "domain-structure"),
                )
            )

        if (
            deceptive_brand_pattern is None
            and not self._is_official_brand_target(normalized_url)
            and self._misleading_subdomain(subdomain_labels, keyword_matches)
        ):
            signals.append(
                self._signal(
                    signal_type=SignalType.MISLEADING_SUBDOMAIN,
                    severity=SignalSeverity.HIGH if len(subdomain_labels) >= 3 else SignalSeverity.MEDIUM,
                    confidence=min(91, 70 + len(subdomain_labels) * 5 + len(keyword_matches) * 3),
                    message_key="signal.misleading_subdomain_structure",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.subdomain_observed",
                                subdomain=normalized_url.subdomain or "(none)",
                            ),
                            evidence_ref(
                                "evidence.registered_domain_observed",
                                registered_domain=normalized_url.registered_domain,
                            ),
                        ]
                    },
                    tags=tuple(subdomain_labels[:4]),
                )
            )

        entropy_label = self._high_entropy_label(host_labels)
        if entropy_label is not None:
            signals.append(
                self._signal(
                    signal_type=SignalType.HIGH_DOMAIN_ENTROPY,
                    severity=SignalSeverity.MEDIUM,
                    confidence=73,
                    message_key="signal.high_entropy_hostname_token",
                    message_params={
                        "evidence": [
                            evidence_ref("evidence.suspicious_label", label=entropy_label)
                        ]
                    },
                    tags=("entropy", "hostname"),
                )
            )

        if tld in _UNCOMMON_BRANDISH_TLDS and (
            brand_matches
            or keyword_matches
            or (institution_context_matches and institution_demand_matches)
        ):
            signals.append(
                self._signal(
                    signal_type=SignalType.TLD_TYPOSQUATTING,
                    severity=SignalSeverity.MEDIUM,
                    confidence=75,
                    message_key="signal.brand_like_domain_on_uncommon_tld",
                    message_params={
                        "evidence": [evidence_ref("evidence.observed_tld", tld=tld)]
                    },
                    tags=("tld", tld),
                )
            )

        if self._is_recognized_reputable_domain(normalized_url):
            signals.append(
                self._signal(
                    signal_type=SignalType.RECOGNIZED_REPUTABLE_DOMAIN,
                    severity=SignalSeverity.LOW,
                    confidence=96,
                    message_key="signal.recognized_reputable_domain",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.registered_domain_observed",
                                registered_domain=normalized_url.registered_domain,
                            )
                        ]
                    },
                    tags=("trust-context", normalized_url.registered_domain),
                )
            )

        return signals

    def _signal(
        self,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        message_key: str,
        message_params: dict[str, object],
        tags: tuple[str, ...] = (),
    ) -> AnalysisSignal:
        return build_localized_signal(
            signal_type=signal_type,
            category=SIGNAL_CATEGORY_MAP[signal_type],
            severity=severity,
            confidence=ConfidenceScore(confidence),
            source=self.source,
            base_weight=BASE_SIGNAL_WEIGHTS[signal_type],
            message_key=message_key,
            message_params=message_params,
            tags=tags,
        )

    def _redirect_indicators(self, normalized_url: NormalizedUrl) -> list[str]:
        indicators: list[dict[str, object]] = []
        path_tokens = _tokenize(normalized_url.decoded_path.replace("/", " "))
        if {"redirect", "continue", "out", "away"}.intersection(path_tokens):
            indicators.append(
                evidence_ref(
                    "evidence.path_contains_redirect_style_tokens",
                    decoded_path=normalized_url.decoded_path,
                )
            )

        for key, value in parse_qsl(normalized_url.query, keep_blank_values=True):
            if key.lower() in _REDIRECT_KEYS:
                indicators.append(
                    evidence_ref(
                        "evidence.query_parameter_may_steer_navigation",
                        key=key,
                        value=value or "(empty)",
                    )
                )
            if value.startswith("http://") or value.startswith("https://"):
                indicators.append(
                    evidence_ref(
                        "evidence.query_parameter_embeds_nested_url",
                        key=key,
                    )
                )

        return indicators

    def _misleading_subdomain(
        self,
        subdomain_labels: list[str],
        keyword_matches: list[str],
    ) -> bool:
        if len(subdomain_labels) >= 3:
            return True
        if not subdomain_labels:
            return False
        subdomain_tokens = {token for label in subdomain_labels for token in _tokenize(label.replace("-", " "))}
        return bool(_SUSPICIOUS_KEYWORDS.intersection(subdomain_tokens))

    def _high_entropy_label(self, labels: list[str]) -> str | None:
        for label in labels:
            if len(label) < 10:
                continue
            if label.isdigit():
                continue
            if _looks_like_readable_compound(label):
                continue
            entropy = _shannon_entropy(label)
            digit_ratio = sum(char.isdigit() for char in label) / len(label)
            if entropy >= 3.5 or digit_ratio >= 0.3:
                return label
        return None

    def _official_brand_domains(self) -> set[str]:
        return {
            "amazon.com",
            "apple.com",
            "appleid.apple.com",
            "bankofamerica.com",
            "dhl.com",
            "dropbox.com",
            "facebook.com",
            "google.com",
            "hmrc.gov.uk",
            "instagram.com",
            "irs.gov",
            "microsoft.com",
            "microsoftonline.com",
            "netflix.com",
            "openai.com",
            "onedrive.live.com",
            "outlook.com",
            "paypal.com",
            "ssa.gov",
            "usps.com",
        }

    def _is_official_brand_target(self, normalized_url: NormalizedUrl) -> bool:
        official_domains = self._official_brand_domains()
        return (
            normalized_url.ascii_host in official_domains
            or normalized_url.registered_domain in official_domains
        )

    def _is_official_institution_target(self, normalized_url: NormalizedUrl) -> bool:
        if self._is_official_brand_target(normalized_url):
            return True

        return normalized_url.ascii_host.endswith(_OFFICIAL_INSTITUTION_SUFFIXES)

    def _is_official_auth_flow(
        self,
        normalized_url: NormalizedUrl,
        keyword_matches: list[str],
    ) -> bool:
        if not self._is_official_brand_target(normalized_url):
            return False

        return set(keyword_matches).issubset(_GENERIC_AUTH_KEYWORDS)

    def _is_recognized_reputable_domain(self, normalized_url: NormalizedUrl) -> bool:
        if normalized_url.registered_domain not in _REPUTABLE_REGISTERED_DOMAINS:
            return False
        if normalized_url.is_ip_address:
            return False
        if normalized_url.contains_unicode or normalized_url.contains_punycode:
            return False
        return True

    def _deceptive_brand_subdomain_pattern(self, subdomain_labels: list[str]) -> str | None:
        if len(subdomain_labels) < 2:
            return None

        for left_label, right_label in zip(subdomain_labels, subdomain_labels[1:]):
            left_tokens = _tokenize(left_label.replace("-", " "))
            matched_brands = sorted(_BRAND_KEYWORDS.intersection(left_tokens))
            if not matched_brands:
                continue
            if right_label not in _COMMON_DOMAIN_SUFFIXES:
                continue
            return f"{matched_brands[0]}.{right_label}"

        return None


def _tokenize(value: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(value)}


def _shannon_entropy(value: str) -> float:
    counts = {char: value.count(char) for char in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def _looks_like_readable_compound(label: str) -> bool:
    if "-" not in label:
        return False

    segments = [segment for segment in label.split("-") if segment]
    return len(segments) >= 2 and all(segment.isalpha() and len(segment) >= 3 for segment in segments)
