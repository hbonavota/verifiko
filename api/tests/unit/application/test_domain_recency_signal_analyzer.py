from datetime import UTC, datetime

from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
    DomainRegistrationLookupError,
)
from app.application.services.domain_recency_signal_analyzer import (
    DomainRecencySignalAnalyzer,
)
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.normalized_url import NormalizedUrl


class StubDomainAgeLookup(DomainAgeLookupPort):
    def __init__(
        self, result: DomainRegistrationInfo | None = None, fail: bool = False
    ) -> None:
        self._result = result
        self._fail = fail

    def lookup(self, domain: str) -> DomainRegistrationInfo | None:
        if self._fail:
            raise DomainRegistrationLookupError(f"lookup failed for {domain}")
        return self._result


def test_domain_recency_signal_analyzer_emits_signal_for_very_recent_domain() -> None:
    analyzer = DomainRecencySignalAnalyzer(
        domain_age_lookup=StubDomainAgeLookup(
            DomainRegistrationInfo(
                registered_at=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                provider_name="stub-rdap",
            )
        ),
        current_time_provider=lambda: datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
    )

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://example.test/login"))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == SignalType.RECENT_DOMAIN_REGISTRATION
    assert signal.severity == SignalSeverity.HIGH
    assert "Observed domain: example.test." in signal.evidence
    assert "Registration date: 2026-03-14." in signal.evidence
    assert "Computed domain age: 3 day(s)." in signal.evidence
    assert "Lookup provider: stub-rdap." in signal.evidence


def test_domain_recency_signal_analyzer_skips_older_domain() -> None:
    analyzer = DomainRecencySignalAnalyzer(
        domain_age_lookup=StubDomainAgeLookup(
            DomainRegistrationInfo(
                registered_at=datetime(2025, 12, 1, 12, 0, tzinfo=UTC),
                provider_name="stub-rdap",
            )
        ),
        current_time_provider=lambda: datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
    )

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://example.test/login"))

    assert signals == []


def test_domain_recency_signal_analyzer_skips_lookup_failures() -> None:
    analyzer = DomainRecencySignalAnalyzer(
        domain_age_lookup=StubDomainAgeLookup(fail=True),
        current_time_provider=lambda: datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
    )

    signals = analyzer.analyze(NormalizedUrl.from_raw("https://example.test/login"))

    assert signals == []


def test_domain_recency_signal_analyzer_reports_lookup_failure_context() -> None:
    analyzer = DomainRecencySignalAnalyzer(
        domain_age_lookup=StubDomainAgeLookup(fail=True),
        current_time_provider=lambda: datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
    )

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://example.test/login")
    )

    assert result.signals == ()
    assert result.warnings == (
        "Domain registration intelligence was unavailable for this run.",
    )
