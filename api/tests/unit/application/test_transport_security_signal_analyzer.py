from app.application.ports.tls_validator import TlsValidationResult, TlsValidatorPort
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.normalized_url import NormalizedUrl


class StubTlsValidator(TlsValidatorPort):
    def __init__(self, result: TlsValidationResult) -> None:
        self._result = result

    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        return self._result


def test_transport_security_signal_analyzer_emits_http_signal() -> None:
    analyzer = TransportSecuritySignalAnalyzer(
        tls_validator=StubTlsValidator(
            TlsValidationResult(is_valid=True, provider_name="stub-tls")
        )
    )

    signals = analyzer.analyze(NormalizedUrl.from_raw("http://portal-example.test/login"))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == SignalType.INSECURE_TRANSPORT
    assert signal.severity == SignalSeverity.HIGH
    assert "Observed URL scheme: http." in signal.evidence
    assert "Matched sensitive URL terms: login." in signal.evidence


def test_transport_security_signal_analyzer_emits_tls_failure_signal() -> None:
    analyzer = TransportSecuritySignalAnalyzer(
        tls_validator=StubTlsValidator(
            TlsValidationResult(
                is_valid=False,
                provider_name="stub-tls",
                failure_reason="certificate verify failed",
            )
        )
    )

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://portal-example.test/login"))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == SignalType.TLS_VALIDATION_FAILURE
    assert "Validated host: portal-example.test." in signal.evidence
    assert "Validation provider: stub-tls." in signal.evidence
    assert "TLS failure reason: certificate verify failed." in signal.evidence


def test_transport_security_signal_analyzer_skips_valid_https() -> None:
    analyzer = TransportSecuritySignalAnalyzer(
        tls_validator=StubTlsValidator(
            TlsValidationResult(is_valid=True, provider_name="stub-tls")
        )
    )

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://portal-example.test/home"))

    assert signals == []
