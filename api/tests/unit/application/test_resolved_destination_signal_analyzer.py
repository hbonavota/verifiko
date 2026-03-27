from app.application.ports.html_fetcher import FetchedHtmlDocument, HtmlFetchError, HtmlFetcherPort
from app.application.ports.redirect_resolver import RedirectHop, RedirectResolution
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.resolved_destination_signal_analyzer import (
    ResolvedDestinationSignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.domain.value_objects.normalized_url import NormalizedUrl


class FakeHtmlFetcher(HtmlFetcherPort):
    def __init__(
        self,
        document: FetchedHtmlDocument | None = None,
        fail: bool = False,
    ) -> None:
        self._document = document
        self._fail = fail

    def fetch(self, url: str) -> FetchedHtmlDocument | None:
        if self._fail:
            raise HtmlFetchError("resolved destination fetch failed")
        return self._document


def _build_analyzer(html_fetcher: HtmlFetcherPort | None = None) -> ResolvedDestinationSignalAnalyzer:
    return ResolvedDestinationSignalAnalyzer(
        url_signal_analyzer=DeterministicUrlSignalAnalyzer(),
        html_fetcher=html_fetcher or FakeHtmlFetcher(),
        html_credential_signal_analyzer=HtmlCredentialSignalAnalyzer(),
    )


def test_resolved_destination_signal_analyzer_skips_same_host_redirects() -> None:
    analyzer = _build_analyzer()
    resolution = RedirectResolution(
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

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://www.example.com/login"),
        redirect_resolution=resolution,
    )

    assert result.signals == ()
    assert result.warnings == ()


def test_resolved_destination_signal_analyzer_skips_same_domain_redirects() -> None:
    analyzer = _build_analyzer()
    resolution = RedirectResolution(
        final_url="https://login.example.com/verify",
        hops=(
            RedirectHop(
                status_code=302,
                source_url="https://www.example.com/out",
                target_url="https://login.example.com/verify",
            ),
        ),
        provider_name="stub-redirect",
    )

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://www.example.com/out"),
        redirect_resolution=resolution,
    )

    assert result.signals == ()
    assert result.warnings == ()


def test_resolved_destination_signal_analyzer_adds_url_signals_for_cross_domain_target() -> None:
    analyzer = _build_analyzer()
    resolution = RedirectResolution(
        final_url="https://paypal-login-security-check.example.xyz/verify",
        hops=(
            RedirectHop(
                status_code=302,
                source_url="https://safe.example/out",
                target_url="https://paypal-login-security-check.example.xyz/verify",
            ),
        ),
        provider_name="stub-redirect",
    )

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://safe.example/out"),
        redirect_resolution=resolution,
    )

    assert any(signal.signal_type.value == "brand_impersonation" for signal in result.signals)
    assert any(signal.source == "resolved-destination-url-analyzer" for signal in result.signals)
    assert result.signals[0].evidence[0].startswith("Resolved final URL:")


def test_resolved_destination_signal_analyzer_adds_html_signals_for_cross_domain_target() -> None:
    analyzer = _build_analyzer(
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Sign in to verify your account</h1>
                    <form action=\"https://collector.bad.example/submit\">
                      <input type=\"email\" name=\"email\" />
                      <input type=\"password\" name=\"password\" />
                      <button type=\"submit\">Sign in</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://collector.bad.example/login",
                content_type="text/html; charset=utf-8",
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

    assert any(signal.signal_type.value == "credential_harvest_form" for signal in result.signals)
    assert any(signal.source == "resolved-destination-html-analyzer" for signal in result.signals)


def test_resolved_destination_signal_analyzer_records_warning_on_fetch_failure() -> None:
    analyzer = _build_analyzer(html_fetcher=FakeHtmlFetcher(fail=True))
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

    assert result.warnings == ("resolved destination fetch failed",)


def test_resolved_destination_signal_analyzer_skips_benign_redirect_interstitial_html() -> None:
    analyzer = _build_analyzer(
        html_fetcher=FakeHtmlFetcher(
            FetchedHtmlDocument(
                content="""
                <html>
                  <body>
                    <h1>Verify redirect</h1>
                    <p>Before continuing, complete this redirect check.</p>
                    <form action="/redirecionamento/7k3qpqd">
                      <input type="password" name="access_code" />
                      <button type="submit">Continue</button>
                    </form>
                  </body>
                </html>
                """,
                source_url="https://www.encurtador.dev/redirecionamento/7k3qpqd",
                content_type="text/html; charset=utf-8",
            )
        )
    )
    resolution = RedirectResolution(
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

    result = analyzer.analyze_with_context(
        NormalizedUrl.from_raw("https://sl1nk.com/7k3qpqd"),
        redirect_resolution=resolution,
    )

    assert all(signal.signal_type.value != "credential_harvest_form" for signal in result.signals)
