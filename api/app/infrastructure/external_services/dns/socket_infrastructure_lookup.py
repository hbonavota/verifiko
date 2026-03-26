import ipaddress
import socket
from dataclasses import dataclass

from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupError,
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
    assert_safe_outbound_host,
)


@dataclass(slots=True)
class SocketInfrastructureLookup(InfrastructureLookupPort):
    provider_name: str = "socket-dns-intelligence"
    max_reverse_lookups: int = 3

    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        try:
            assert_safe_outbound_host(hostname, port)
        except UnsafeOutboundTargetError as exc:
            raise InfrastructureLookupError(str(exc)) from exc

        try:
            addrinfo = socket.getaddrinfo(
                hostname,
                port or 443,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise InfrastructureLookupError(
                "DNS resolution could not be completed for the target host."
            ) from exc

        resolved_addresses: list[ResolvedAddress] = []
        seen_ips: set[str] = set()
        for _, _, _, _, sockaddr in addrinfo:
            ip_address = str(ipaddress.ip_address(sockaddr[0]))
            if ip_address in seen_ips:
                continue
            seen_ips.add(ip_address)
            reverse_hostname = None
            if len(resolved_addresses) < self.max_reverse_lookups:
                reverse_hostname = self._reverse_lookup(ip_address)
            resolved_addresses.append(
                ResolvedAddress(
                    ip_address=ip_address,
                    reverse_hostname=reverse_hostname,
                )
            )

        if not resolved_addresses:
            raise InfrastructureLookupError("DNS resolution returned no usable addresses.")

        return InfrastructureProfile(
            queried_host=hostname,
            provider_name=self.provider_name,
            resolved_addresses=tuple(resolved_addresses),
        )

    def _reverse_lookup(self, ip_address: str) -> str | None:
        try:
            host, _, _ = socket.gethostbyaddr(ip_address)
        except (socket.herror, socket.gaierror, OSError):
            return None
        return host.lower().rstrip(".")
