import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl

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
}
_EMAIL_LURE_KEYWORDS = {"mail", "mailbox", "office365", "outlook", "webmail"}
_SHORTENER_DOMAINS = {
    "bit.ly",
    "cutt.ly",
    "goo.gl",
    "is.gd",
    "ow.ly",
    "rebrand.ly",
    "rb.gy",
    "t.co",
    "tinyurl.com",
}
_UNCOMMON_BRANDISH_TLDS = {"buzz", "click", "gq", "info", "link", "live", "rest", "shop", "top", "xyz"}
_COMMON_DOMAIN_SUFFIXES = {"ac", "app", "biz", "co", "com", "dev", "edu", "gov", "info", "io", "net", "org"}
_REDIRECT_KEYS = {"continue", "next", "redirect", "return", "target", "url"}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


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
        deceptive_brand_pattern = self._deceptive_brand_subdomain_pattern(subdomain_labels)
        tld = host_labels[-1] if len(host_labels) >= 2 else ""

        if normalized_url.is_ip_address:
            signals.append(
                self._signal(
                    signal_type=SignalType.IP_ADDRESS_URL,
                    severity=SignalSeverity.HIGH,
                    confidence=96,
                    title="Direct IP address target",
                    description="The input targets an IP address directly instead of a named host.",
                    evidence=(f"Host resolves to raw IP {normalized_url.ascii_host}.",),
                    tags=("ip-host", "domain-structure"),
                )
            )

        if normalized_url.contains_unicode or normalized_url.contains_punycode:
            evidence = []
            if normalized_url.contains_unicode:
                evidence.append(f"Rendered host: {normalized_url.host}.")
            if normalized_url.contains_punycode:
                evidence.append(f"ASCII host contains punycode label(s): {normalized_url.ascii_host}.")
            else:
                evidence.append(f"ASCII host: {normalized_url.ascii_host}.")

            signals.append(
                self._signal(
                    signal_type=SignalType.UNICODE_HOMOGRAPH,
                    severity=SignalSeverity.HIGH,
                    confidence=88 if normalized_url.contains_unicode else 84,
                    title="Unicode or punycode hostname pattern",
                    description=(
                        "The hostname contains unicode characters or punycode labels that merit "
                        "homograph review."
                    ),
                    evidence=tuple(evidence),
                    tags=("unicode-host", "homograph-review"),
                )
            )

        if normalized_url.contains_zero_width_chars:
            signals.append(
                self._signal(
                    signal_type=SignalType.ZERO_WIDTH_CHAR_INJECTION,
                    severity=SignalSeverity.CRITICAL,
                    confidence=99,
                    title="Invisible hostname characters",
                    description="Zero-width characters were found in the hostname representation.",
                    evidence=(f"Host contains zero-width characters: {normalized_url.host}.",),
                    tags=("zero-width", "hostname-obfuscation"),
                )
            )

        if normalized_url.port is not None and normalized_url.port not in {80, 443}:
            signals.append(
                self._signal(
                    signal_type=SignalType.NON_STANDARD_PORT_USAGE,
                    severity=SignalSeverity.MEDIUM,
                    confidence=74,
                    title="Non-standard port usage",
                    description="The URL uses a non-standard web port, which increases handling risk.",
                    evidence=(f"Observed explicit port {normalized_url.port}.",),
                    tags=("port", "network-transport"),
                )
            )

        if normalized_url.registered_domain in _SHORTENER_DOMAINS:
            signals.append(
                self._signal(
                    signal_type=SignalType.SHORTENED_URL,
                    severity=SignalSeverity.MEDIUM,
                    confidence=82,
                    title="Shortened destination",
                    description="The URL uses a known shortening service that obscures the eventual destination.",
                    evidence=(f"Registered domain {normalized_url.registered_domain} is a shortener.",),
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
                    title="Redirect-style parameters",
                    description="The URL contains redirect-style routing hints that can conceal the final destination.",
                    evidence=tuple(redirect_indicators),
                    tags=("redirect", "navigation"),
                )
            )

        if keyword_matches:
            keyword_sample = ", ".join(keyword_matches[:4])
            signals.append(
                self._signal(
                    signal_type=SignalType.PHISHING_KEYWORDS,
                    severity=SignalSeverity.HIGH if len(keyword_matches) >= 3 else SignalSeverity.MEDIUM,
                    confidence=min(92, 62 + len(keyword_matches) * 7),
                    title="Credential-lure wording in URL",
                    description="The host or path contains account and verification language commonly used in phishing lures.",
                    evidence=(f"Matched URL keywords: {keyword_sample}.",),
                    tags=tuple(keyword_matches[:4]),
                )
            )

        if brand_matches and keyword_matches and normalized_url.registered_domain not in self._official_brand_domains():
            brand_sample = ", ".join(brand_matches[:3])
            signals.append(
                self._signal(
                    signal_type=SignalType.BRAND_IMPERSONATION,
                    severity=SignalSeverity.HIGH,
                    confidence=min(95, 76 + len(brand_matches) * 5 + len(keyword_matches) * 2),
                    title="Brand-like impersonation hints",
                    description="Brand references are combined with account-action language in a non-official domain.",
                    evidence=(
                        f"Matched brand terms: {brand_sample}.",
                        f"Registered domain under review: {normalized_url.registered_domain}.",
                    ),
                    tags=tuple((brand_matches + keyword_matches)[:5]),
                )
            )

        if keyword_matches and _EMAIL_LURE_KEYWORDS.intersection(text_tokens):
            email_terms = sorted(_EMAIL_LURE_KEYWORDS.intersection(text_tokens))
            signals.append(
                self._signal(
                    signal_type=SignalType.TACTICAL_EMAIL_STAGING,
                    severity=SignalSeverity.MEDIUM,
                    confidence=min(90, 72 + len(email_terms) * 6),
                    title="Mailbox access lure pattern",
                    description="The URL combines mailbox-style terms with account-action cues.",
                    evidence=(f"Matched mailbox terms: {', '.join(email_terms)}.",),
                    tags=tuple((email_terms + keyword_matches)[:5]),
                )
            )

        if deceptive_brand_pattern is not None:
            signals.append(
                self._signal(
                    signal_type=SignalType.DECEPTIVE_BRAND_SUBDOMAIN,
                    severity=SignalSeverity.HIGH,
                    confidence=94,
                    title="Deceptive brand-in-subdomain pattern",
                    description="The subdomain embeds a brand-like domain fragment before the actual registered domain.",
                    evidence=(
                        f"Observed deceptive fragment: {deceptive_brand_pattern}.",
                        f"Registered domain observed: {normalized_url.registered_domain}.",
                    ),
                    tags=("brand-subdomain", "domain-structure"),
                )
            )

        if deceptive_brand_pattern is None and self._misleading_subdomain(subdomain_labels, keyword_matches):
            signals.append(
                self._signal(
                    signal_type=SignalType.MISLEADING_SUBDOMAIN,
                    severity=SignalSeverity.HIGH if len(subdomain_labels) >= 3 else SignalSeverity.MEDIUM,
                    confidence=min(91, 70 + len(subdomain_labels) * 5 + len(keyword_matches) * 3),
                    title="Misleading subdomain structure",
                    description="The subdomain structure adds unusual depth or trust-signaling lure wording ahead of the registered domain.",
                    evidence=(
                        f"Subdomain observed: {normalized_url.subdomain or '(none)'}.",
                        f"Registered domain observed: {normalized_url.registered_domain}.",
                    ),
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
                    title="High-entropy hostname token",
                    description="One hostname label appears algorithmically generated or unusually noisy.",
                    evidence=(f"Suspicious label: {entropy_label}.",),
                    tags=("entropy", "hostname"),
                )
            )

        if tld in _UNCOMMON_BRANDISH_TLDS and (brand_matches or keyword_matches):
            signals.append(
                self._signal(
                    signal_type=SignalType.TLD_TYPOSQUATTING,
                    severity=SignalSeverity.MEDIUM,
                    confidence=75,
                    title="Brand-like domain on uncommon TLD",
                    description="The hostname mixes brand or account language with a higher-risk TLD choice.",
                    evidence=(f"Observed TLD: .{tld}.",),
                    tags=("tld", tld),
                )
            )

        return signals

    def _signal(
        self,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        title: str,
        description: str,
        evidence: tuple[str, ...],
        tags: tuple[str, ...] = (),
    ) -> AnalysisSignal:
        return AnalysisSignal.create(
            signal_type=signal_type,
            category=SIGNAL_CATEGORY_MAP[signal_type],
            severity=severity,
            confidence=ConfidenceScore(confidence),
            title=title,
            description=description,
            source=self.source,
            base_weight=BASE_SIGNAL_WEIGHTS[signal_type],
            evidence=evidence,
            tags=tags,
        )

    def _redirect_indicators(self, normalized_url: NormalizedUrl) -> list[str]:
        indicators: list[str] = []
        path_tokens = _tokenize(normalized_url.decoded_path.replace("/", " "))
        if {"redirect", "continue", "out", "away"}.intersection(path_tokens):
            indicators.append(
                f"Path contains redirect-style token(s): {normalized_url.decoded_path}."
            )

        for key, value in parse_qsl(normalized_url.query, keep_blank_values=True):
            if key.lower() in _REDIRECT_KEYS:
                indicators.append(f"Query parameter {key}={value or '(empty)'} may steer navigation.")
            if value.startswith("http://") or value.startswith("https://"):
                indicators.append(f"Query parameter {key} embeds a nested URL destination.")

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
            "instagram.com",
            "microsoft.com",
            "netflix.com",
            "openai.com",
            "onedrive.live.com",
            "outlook.com",
            "paypal.com",
        }

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
