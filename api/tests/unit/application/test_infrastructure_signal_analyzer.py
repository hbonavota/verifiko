from app.application.ports.infrastructure_lookup import (
    InfrastructureLookupError,
    InfrastructureLookupPort,
    InfrastructureProfile,
    ResolvedAddress,
)
from app.application.ports.redirect_resolver import RedirectHop, RedirectResolution
from app.application.services.infrastructure_signal_analyzer import InfrastructureSignalAnalyzer
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.normalized_url import NormalizedUrl


class StubInfrastructureLookup(InfrastructureLookupPort):
    def __init__(self, profile: InfrastructureProfile) -> None:
        self._profile = profile

    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        return self._profile


class FailingInfrastructureLookup(InfrastructureLookupPort):
    def lookup(self, hostname: str, port: int | None = None) -> InfrastructureProfile:
        raise InfrastructureLookupError("lookup unavailable")


def test_infrastructure_signal_analyzer_flags_dynamic_dns_reverse_host() -> None:
    analyzer = InfrastructureSignalAnalyzer(
        infrastructure_lookup=StubInfrastructureLookup(
            InfrastructureProfile(
                queried_host="login.safe-example.test",
                provider_name="stub-infrastructure",
                resolved_addresses=(
                    ResolvedAddress(
                        ip_address="203.0.113.44",
                        reverse_hostname="cust-203-0-113-44.no-ip.org",
                    ),
                ),
            )
        )
    )

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://login.safe-example.test/verify")
    )

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN
    assert signal.severity == SignalSeverity.HIGH
    assert "Matched infrastructure patterns: dynamic-dns, residential-ptr." in signal.evidence
    assert signal.message_params["evidence"][3]["params"]["patterns"] == [
        {"key": "phrase.infrastructure_pattern_dynamic_dns", "params": {}},
        {"key": "phrase.infrastructure_pattern_residential_ptr", "params": {}},
    ]


def test_infrastructure_signal_analyzer_skips_benign_cdn_reverse_host() -> None:
    analyzer = InfrastructureSignalAnalyzer(
        infrastructure_lookup=StubInfrastructureLookup(
            InfrastructureProfile(
                queried_host="www.example.com",
                provider_name="stub-infrastructure",
                resolved_addresses=(
                    ResolvedAddress(
                        ip_address="203.0.113.10",
                        reverse_hostname="a23-45-67-89.deploy.static.akamaitechnologies.com",
                    ),
                ),
            )
        )
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://www.example.com"))

    assert result.signals == ()
    assert result.warnings == ()


def test_infrastructure_signal_analyzer_uses_redirect_target() -> None:
    analyzer = InfrastructureSignalAnalyzer(
        infrastructure_lookup=StubInfrastructureLookup(
            InfrastructureProfile(
                queried_host="collector.bad.example",
                provider_name="stub-infrastructure",
                resolved_addresses=(
                    ResolvedAddress(
                        ip_address="203.0.113.88",
                        reverse_hostname="pool-203-0-113-88.dynamic.example.net",
                    ),
                ),
            )
        )
    )
    resolution = RedirectResolution(
        final_url="https://collector.bad.example/login",
        hops=(
            RedirectHop(
                status_code=302,
                source_url="https://safe.example/out",
                target_url="https://collector.bad.example/login",
            ),
        ),
        provider_name="stub-redirect",
    )

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://safe.example/out"),
        redirect_resolution=resolution,
    )

    assert len(result.signals) == 1
    assert "Effective target derived from redirect chain: https://collector.bad.example/login." in (
        result.signals[0].evidence
    )


def test_infrastructure_signal_analyzer_records_warning_when_lookup_fails() -> None:
    analyzer = InfrastructureSignalAnalyzer(
        infrastructure_lookup=FailingInfrastructureLookup()
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://openai.com"))

    assert result.signals == ()
    assert result.warnings == ("Infrastructure intelligence could not be completed for this run.",)
