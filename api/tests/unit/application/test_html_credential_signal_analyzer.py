from app.application.ports.html_fetcher import FetchedHtmlDocument
from app.application.services.html_credential_signal_analyzer import (
    HtmlCredentialSignalAnalyzer,
)
from app.domain.enums.signal_type import SignalType
from app.domain.value_objects.normalized_url import NormalizedUrl


def test_html_credential_signal_analyzer_emits_signal_for_login_form() -> None:
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://portal-example.test/login"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>Verify your account</h1>
                <form action="https://collector.bad.example/submit">
                  <input type="email" name="email" />
                  <input type="password" name="password" />
                  <button type="submit">Sign in</button>
                </form>
              </body>
            </html>
            """,
            source_url="https://portal-example.test/login",
            content_type="text/html",
        ),
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == SignalType.CREDENTIAL_HARVEST_FORM
    assert "HTML forms found: 1." in signal.evidence
    assert "Password fields found: 1." in signal.evidence
    assert "Matched account input hints: email." in signal.evidence
    assert "Matched login wording: account, sign in, verify." in signal.evidence
    assert (
        "Suspicious form action: https://collector.bad.example/submit."
        in signal.evidence
    )


def test_html_credential_signal_analyzer_skips_pages_without_login_patterns() -> None:
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://portal-example.test/about"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>About our company</h1>
                <p>Read the latest platform updates, product news, developer documentation,
                support resources, release notes, service information, and company background.</p>
              </body>
            </html>
            """,
            source_url="https://portal-example.test/about",
            content_type="text/html",
        ),
    )

    assert signals == []


def test_html_credential_signal_analyzer_skips_generic_legitimate_login_surface() -> (
    None
):
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://github.com"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <nav>
                  <a href="/login">Sign in</a>
                  <a href="/signup">Create account</a>
                </nav>
                <form action="/session">
                  <input type="email" name="user_email" />
                  <button type="submit">Sign in</button>
                </form>
              </body>
            </html>
            """,
            source_url="https://github.com",
            content_type="text/html",
        ),
    )

    assert all(
        signal.signal_type != SignalType.SUSPICIOUS_LOGIN_INTERFACE
        for signal in signals
    )


def test_html_credential_signal_analyzer_emits_signal_for_suspicious_login_ui() -> None:
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://secure-login.bad-example.test/"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>Verify account sign in</h1>
                <form action="https://collector.bad.example/submit">
                  <input type="email" name="email" />
                  <button type="submit">Sign in</button>
                </form>
              </body>
            </html>
            """,
            source_url="https://secure-login.bad-example.test/",
            content_type="text/html",
        ),
    )

    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.SUSPICIOUS_LOGIN_INTERFACE


def test_html_credential_signal_analyzer_emits_signal_for_challenge_approval_surface() -> (
    None
):
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://secure-login.bad-example.test/"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>Security challenge</h1>
                <p>Approve this verification to continue your account session.</p>
                <form action="/checkpoint">
                  <input type="text" name="otp_code" />
                  <button type="submit">Approve</button>
                </form>
              </body>
            </html>
            """,
            source_url="https://secure-login.bad-example.test/",
            content_type="text/html",
        ),
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == SignalType.SUSPICIOUS_LOGIN_INTERFACE
    assert "Matched authentication input hints: otp." in signal.evidence
    assert (
        "Matched login wording: account, approve, challenge, security."
        in signal.evidence
    )
    assert (
        "Observed form action: https://secure-login.bad-example.test/checkpoint."
        in signal.evidence
    )


def test_html_credential_signal_analyzer_skips_official_same_site_challenge_surface() -> (
    None
):
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://accounts.google.com/challenge"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>Security challenge</h1>
                <p>Approve this verification to continue your account session.</p>
                <form action="/challenge">
                  <input type="text" name="otp_code" />
                  <button type="submit">Approve</button>
                </form>
              </body>
            </html>
            """,
            source_url="https://accounts.google.com/challenge",
            content_type="text/html",
        ),
    )

    assert signals == []


def test_html_credential_signal_analyzer_skips_same_site_redirect_interstitial_with_weak_terms() -> (
    None
):
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://www.encurtador.dev/redirecionamento/7k3qpqd"),
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
            content_type="text/html",
        ),
    )

    assert signals == []


def test_html_credential_signal_analyzer_flags_parked_placeholder_pages() -> None:
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://for-sale-example.test/"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>This domain is for sale</h1>
                <p>Buy this domain with Sedo.</p>
              </body>
            </html>
            """,
            source_url="https://for-sale-example.test/",
            content_type="text/html",
        ),
    )

    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.LOW_INFORMATION_PAGE
    assert signals[0].title == "Parked or placeholder landing page"
    assert (
        "Matched placeholder markers: buy this domain, sedo, this domain is for sale."
        in signals[0].evidence
    )


def test_html_credential_signal_analyzer_flags_extremely_low_information_root_pages() -> (
    None
):
    analyzer = HtmlCredentialSignalAnalyzer()

    signals = analyzer.analyze(
        NormalizedUrl.from_raw("https://thin-example.test/"),
        FetchedHtmlDocument(
            content="""
            <html>
              <body>
                <h1>Welcome</h1>
              </body>
            </html>
            """,
            source_url="https://thin-example.test/",
            content_type="text/html",
        ),
    )

    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.LOW_INFORMATION_PAGE
    assert signals[0].title == "Low-information landing page"
    assert "Visible text tokens found: 1." in signals[0].evidence
