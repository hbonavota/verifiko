from app.application.ports.redirect_resolver import (
    RedirectHop,
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.domain.value_objects.normalized_url import NormalizedUrl


class FakeRedirectResolver(RedirectResolverPort):
    def __init__(
        self,
        result: RedirectResolution | None = None,
        fail: bool = False,
    ) -> None:
        self._result = result or RedirectResolution(
            final_url="https://example.test/",
            hops=(),
            provider_name="stub-redirect",
        )
        self._fail = fail

    def resolve(self, url: str) -> RedirectResolution:
        if self._fail:
            raise RedirectResolutionError("redirect lookup failed")
        return self._result


def test_redirect_signal_analyzer_skips_same_domain_canonical_redirects() -> None:
    analyzer = RedirectSignalAnalyzer(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://www.example.com/login",
                hops=(
                    RedirectHop(
                        status_code=301,
                        source_url="https://example.com/login",
                        target_url="https://www.example.com/login",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://example.com/login"))

    assert result.signals == ()
    assert result.redirect_resolution is not None


def test_redirect_signal_analyzer_flags_cross_domain_chain() -> None:
    analyzer = RedirectSignalAnalyzer(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://collector.bad.example/login",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://short.example/abc",
                        target_url="https://collector.bad.example/login",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://short.example/abc"))

    assert len(result.signals) == 1
    assert result.signals[0].signal_type.value == "suspicious_redirect_chain"
    assert "Final URL after redirects: https://collector.bad.example/login." in (
        result.signals[0].evidence
    )
    assert result.signals[0].severity.value == "HIGH"


def test_redirect_signal_analyzer_skips_clean_single_hop_interstitial_redirect() -> None:
    analyzer = RedirectSignalAnalyzer(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://www.encurtador.dev/redirecionamento/7k3qpqd",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://sl1nk.com/7k3qpqd",
                        target_url="https://www.encurtador.dev/redirecionamento/7k3qpqd",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://sl1nk.com/7k3qpqd"))

    assert result.signals == ()
    assert result.redirect_resolution is not None


def test_redirect_signal_analyzer_skips_clean_single_hop_shortener_redirect() -> None:
    analyzer = RedirectSignalAnalyzer(
        redirect_resolver=FakeRedirectResolver(
            RedirectResolution(
                final_url="https://openai.com/",
                hops=(
                    RedirectHop(
                        status_code=302,
                        source_url="https://g.co/openai",
                        target_url="https://openai.com/",
                    ),
                ),
                provider_name="stub-redirect",
            )
        )
    )

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://g.co/openai"))

    assert result.signals == ()
    assert result.redirect_resolution is not None


def test_redirect_signal_analyzer_records_warning_when_resolution_fails() -> None:
    analyzer = RedirectSignalAnalyzer(redirect_resolver=FakeRedirectResolver(fail=True))

    result = analyzer.analyze_with_context(NormalizedUrl.from_raw("https://example.com"))

    assert result.signals == ()
    assert result.warnings == ("Redirect resolution could not be completed for this run.",)
