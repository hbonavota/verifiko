import re
from dataclasses import dataclass

from app.application.ports.tls_validator import (
    TlsValidationError,
    TlsValidationResult,
    TlsValidatorPort,
)
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
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
        signals: list[AnalysisSignal] = []
        sensitive_terms = self._sensitive_terms(normalized_url)

        if normalized_url.scheme == "http":
            signals.append(self._insecure_transport_signal(normalized_url, sensitive_terms))
            return signals

        if normalized_url.scheme != "https" or normalized_url.is_ip_address:
            return signals

        try:
            validation_result = self.tls_validator.validate_hostname(
                normalized_url.ascii_host,
                normalized_url.port or 443,
            )
        except TlsValidationError:
            return signals

        if not validation_result.is_valid:
            signals.append(
                self._tls_validation_failure_signal(
                    normalized_url=normalized_url,
                    validation_result=validation_result,
                    sensitive_terms=sensitive_terms,
                )
            )

        return signals

    def _insecure_transport_signal(
        self,
        normalized_url: NormalizedUrl,
        sensitive_terms: list[str],
    ) -> AnalysisSignal:
        is_sensitive_target = bool(sensitive_terms)
        evidence = [
            f"Observed URL scheme: {normalized_url.scheme}.",
            f"Observed host: {normalized_url.ascii_host}.",
        ]
        if sensitive_terms:
            evidence.append(f"Matched sensitive URL terms: {', '.join(sensitive_terms[:4])}.")

        return self._signal(
            signal_type=SignalType.INSECURE_TRANSPORT,
            severity=SignalSeverity.HIGH if is_sensitive_target else SignalSeverity.MEDIUM,
            confidence=92 if is_sensitive_target else 80,
            title="Insecure transport scheme",
            description=(
                "The target uses plain HTTP without TLS protection."
                if not is_sensitive_target
                else "The target uses plain HTTP despite exposing login-oriented or brand-sensitive cues."
            ),
            evidence=tuple(evidence),
            tags=("http", "transport-security"),
        )

    def _tls_validation_failure_signal(
        self,
        normalized_url: NormalizedUrl,
        validation_result: TlsValidationResult,
        sensitive_terms: list[str],
    ) -> AnalysisSignal:
        evidence = [
            f"Observed URL scheme: {normalized_url.scheme}.",
            f"Validated host: {normalized_url.ascii_host}.",
            f"Validation provider: {validation_result.provider_name}.",
        ]
        if validation_result.failure_reason:
            evidence.append(f"TLS failure reason: {validation_result.failure_reason}.")
        if sensitive_terms:
            evidence.append(f"Matched sensitive URL terms: {', '.join(sensitive_terms[:4])}.")

        return self._signal(
            signal_type=SignalType.TLS_VALIDATION_FAILURE,
            severity=SignalSeverity.HIGH if sensitive_terms else SignalSeverity.MEDIUM,
            confidence=91 if sensitive_terms else 84,
            title="TLS validation failure",
            description=(
                "The HTTPS endpoint could not be validated with the system TLS trust store."
            ),
            evidence=tuple(evidence),
            tags=("tls", "transport-security"),
        )

    def _signal(
        self,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        title: str,
        description: str,
        evidence: tuple[str, ...],
        tags: tuple[str, ...],
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

    def _sensitive_terms(self, normalized_url: NormalizedUrl) -> list[str]:
        text = " ".join(
            [
                normalized_url.host,
                normalized_url.path.replace("/", " "),
                normalized_url.query.replace("&", " "),
                normalized_url.fragment.replace("/", " "),
            ]
        )
        tokens = {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)}
        return sorted(_SENSITIVE_TERMS.intersection(tokens))
