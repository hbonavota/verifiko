from app.application.ports.redirect_resolver import RedirectHop, RedirectResolution
from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
from app.domain.value_objects.normalized_url import NormalizedUrl


class FakeReputationLookup(ReputationLookupPort):
    def __init__(
        self,
        matches: dict[str, ReputationMatch] | None = None,
        fail: bool = False,
    ) -> None:
        self._matches = matches or {}
        self._fail = fail

    def lookup(self, hostname: str) -> ReputationMatch | None:
        if self._fail:
            raise ReputationLookupError("lookup failed")
        return self._matches.get(hostname)


def test_reputation_signal_analyzer_flags_listed_host() -> None:
    analyzer = ReputationSignalAnalyzer(
        reputation_lookup=FakeReputationLookup(
            {
                "collector.bad.example": ReputationMatch(
                    queried_value="collector.bad.example",
                    provider_name="stub-feed",
                    confidence=99.0,
                    reference_count=4,
                    match_scope="host",
                    description="Known malicious host.",
                )
            }
        )
    )

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://collector.bad.example/login")
    )

    assert len(result.signals) == 1
    assert result.signals[0].signal_type.value == "blacklist_match"
    assert result.signals[0].severity.value == "CRITICAL"


def test_reputation_signal_analyzer_checks_redirect_destination() -> None:
    analyzer = ReputationSignalAnalyzer(
        reputation_lookup=FakeReputationLookup(
            {
                "collector.bad.example": ReputationMatch(
                    queried_value="collector.bad.example",
                    provider_name="stub-feed",
                    confidence=99.0,
                    reference_count=2,
                    match_scope="host",
                    description="Known malicious redirect destination.",
                )
            }
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
    assert "Final redirect target: https://collector.bad.example/login." in (
        result.signals[0].evidence
    )


def test_reputation_signal_analyzer_records_warning_when_lookup_fails() -> None:
    analyzer = ReputationSignalAnalyzer(
        reputation_lookup=FakeReputationLookup(fail=True)
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://openai.com"))

    assert result.signals == ()
    assert result.warnings == (
        "Blacklist reputation intelligence was unavailable for this run.",
    )
