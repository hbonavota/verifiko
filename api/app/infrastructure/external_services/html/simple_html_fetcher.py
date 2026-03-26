from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.application.ports.html_fetcher import (
    FetchedHtmlDocument,
    HtmlFetchError,
    HtmlFetcherPort,
)
from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
    assert_safe_outbound_url,
)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(slots=True)
class SimpleHtmlFetcher(HtmlFetcherPort):
    timeout_seconds: float = 3.0
    max_bytes: int = 200_000
    user_agent: str = "Verifiko/1.0"

    def fetch(self, url: str) -> FetchedHtmlDocument | None:
        try:
            assert_safe_outbound_url(url)
        except UnsafeOutboundTargetError as exc:
            raise HtmlFetchError(
                "HTML content fetch was blocked for a private or special-use target."
            ) from exc

        request = Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": self.user_agent,
            },
        )

        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get("Content-Type")
                if content_type is not None and "html" not in content_type.lower():
                    return None

                raw_content = response.read(self.max_bytes)
                encoding = response.headers.get_content_charset() or "utf-8"
                content = raw_content.decode(encoding, errors="replace")
                return FetchedHtmlDocument(
                    content=content,
                    source_url=response.geturl(),
                    content_type=content_type,
                )
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError) as exc:
            raise HtmlFetchError(str(exc)) from exc
