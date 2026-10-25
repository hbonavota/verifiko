import re
from dataclasses import dataclass

from app.application.ports.tls_validator import (
    TlsValidationError,
    TlsValidationResult,
    TlsValidatorPort,
)
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.message_resolver import (
    build_localized_signal,
    evidence_ref,
    normalize_tls_failure_reason,
    resolve_message,
)
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import (
    BASE_SIGNAL_WEIGHTS,
    SIGNAL_CATEGORY_MAP,
)
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

_SENSITIVE_TERMS = {
    "account",
    "bank",
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
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(slots=True)
class TransportSecuritySignalAnalyzer:
    tls_validator: TlsValidatorPort
    source: str = "transport-security-analyzer"

    def analyze(self, normalized_url: NormalizedUrl) -> list[AnalysisSignal]:
        return list(self.analyze_with_context(normalized_url).signals)

    def analyze_with_context(
        self, normalized_url: NormalizedUrl
    ) -> SignalAnalysisResult:
        signals: list[AnalysisSignal] = []
        sensitive_terms = self._sensitive_terms(normalized_url)

        if normalized_url.scheme == "http":
            signals.append(
                self._insecure_transport_signal(normalized_url, sensitive_terms)
            )
            return SignalAnalysisResult(signals=tuple(signals))

        if normalized_url.scheme != "https" or normalized_url.is_ip_address:
            return SignalAnalysisResult()

        try:
            validation_result = self.tls_validator.validate_hostname(
                normalized_url.ascii_host,
                normalized_url.port or 443,
            )
        except TlsValidationError:
            return SignalAnalysisResult(
                warnings=(resolve_message("warning.tls_validation_unavailable"),)
            )

        if not validation_result.is_valid:
            signals.append(
                self._tls_validation_failure_signal(
                    normalized_url=normalized_url,
                    validation_result=validation_result,
                    sensitive_terms=sensitive_terms,
                )
            )

        return SignalAnalysisResult(signals=tuple(signals))

    def _insecure_transport_signal(
        self,
        normalized_url: NormalizedUrl,
        sensitive_terms: list[str],
    ) -> AnalysisSignal:
        is_sensitive_target = bool(sensitive_terms)
        evidence = [
            evidence_ref("evidence.observed_url_scheme", scheme=normalized_url.scheme),
            evidence_ref("evidence.observed_host", host=normalized_url.ascii_host),
        ]
        if sensitive_terms:
            evidence.append(
                evidence_ref(
                    "evidence.matched_sensitive_url_terms",
                    terms=", ".join(sensitive_terms[:4]),
                )
            )

        return self._signal(
            signal_type=SignalType.INSECURE_TRANSPORT,
            severity=(
                SignalSeverity.HIGH if is_sensitive_target else SignalSeverity.MEDIUM
            ),
            confidence=92 if is_sensitive_target else 80,
            message_key=(
                "signal.insecure_transport_scheme_sensitive"
                if is_sensitive_target
                else "signal.insecure_transport_scheme_plain"
            ),
            message_params={"evidence": evidence},
            tags=("http", "transport-security"),
        )

    def _tls_validation_failure_signal(
        self,
        normalized_url: NormalizedUrl,
        validation_result: TlsValidationResult,
        sensitive_terms: list[str],
    ) -> AnalysisSignal:
        evidence = [
            evidence_ref("evidence.observed_url_scheme", scheme=normalized_url.scheme),
            evidence_ref("evidence.validated_host", host=normalized_url.ascii_host),
            evidence_ref(
                "evidence.validation_provider",
                provider_name=validation_result.provider_name,
            ),
        ]
        if validation_result.failure_reason:
            evidence.append(
                evidence_ref(
                    "evidence.tls_failure_reason",
                    failure_reason=normalize_tls_failure_reason(
                        validation_result.failure_reason
                    ),
                )
            )
        if sensitive_terms:
            evidence.append(
                evidence_ref(
                    "evidence.matched_sensitive_url_terms",
                    terms=", ".join(sensitive_terms[:4]),
                )
            )

        return self._signal(
            signal_type=SignalType.TLS_VALIDATION_FAILURE,
            severity=SignalSeverity.HIGH if sensitive_terms else SignalSeverity.MEDIUM,
            confidence=91 if sensitive_terms else 84,
            message_key="signal.tls_validation_failure",
            message_params={"evidence": evidence},
            tags=("tls", "transport-security"),
        )

    def _signal(
        self,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        message_key: str,
        message_params: dict[str, object],
        tags: tuple[str, ...],
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
