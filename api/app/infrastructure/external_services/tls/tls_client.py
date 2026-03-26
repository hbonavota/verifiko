import socket
import ssl
from dataclasses import dataclass

from app.application.ports.tls_validator import (
    TlsValidationError,
    TlsValidationResult,
    TlsValidatorPort,
)
from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
    assert_safe_outbound_host,
)


@dataclass(slots=True)
class SocketTlsValidator(TlsValidatorPort):
    timeout_seconds: float = 3.0
    provider_name: str = "system-ssl"

    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        context = ssl.create_default_context()

        try:
            assert_safe_outbound_host(hostname, port)
            with socket.create_connection((hostname, port), timeout=self.timeout_seconds) as sock:
                with context.wrap_socket(sock, server_hostname=hostname):
                    return TlsValidationResult(
                        is_valid=True,
                        provider_name=self.provider_name,
                    )
        except ssl.SSLCertVerificationError as exc:
            return TlsValidationResult(
                is_valid=False,
                provider_name=self.provider_name,
                failure_reason=str(exc.verify_message or exc),
            )
        except ssl.SSLError as exc:
            return TlsValidationResult(
                is_valid=False,
                provider_name=self.provider_name,
                failure_reason=str(exc),
            )
        except UnsafeOutboundTargetError as exc:
            raise TlsValidationError(str(exc)) from exc
        except (socket.timeout, socket.gaierror, OSError) as exc:
            raise TlsValidationError(str(exc)) from exc
