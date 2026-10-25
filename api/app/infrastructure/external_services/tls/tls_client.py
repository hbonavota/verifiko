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
    resolve_safe_outbound_host,
)


@dataclass(slots=True)
class SocketTlsValidator(TlsValidatorPort):
    timeout_seconds: float = 3.0
    provider_name: str = "system-ssl"

    def validate_hostname(self, hostname: str, port: int = 443) -> TlsValidationResult:
        context = ssl.create_default_context()
        last_network_error: Exception | None = None

        try:
            resolution = resolve_safe_outbound_host(hostname, port)
            for ip_address in resolution.ip_addresses:
                try:
                    with socket.create_connection(
                        (ip_address, resolution.port),
                        timeout=self.timeout_seconds,
                    ) as sock, context.wrap_socket(
                        sock, server_hostname=resolution.hostname
                    ):
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
                except (TimeoutError, socket.gaierror, OSError) as exc:
                    last_network_error = exc
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
        if last_network_error is not None:
            raise TlsValidationError(str(last_network_error)) from last_network_error
        raise TlsValidationError("No validated outbound address could be reached.")
