from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.application.ports.html_fetcher import (
    FetchedHtmlDocument,
    HtmlFetchError,
    HtmlFetcherPort,
)


@dataclass(slots=True)
class SimpleHtmlFetcher(HtmlFetcherPort):
    timeout_seconds: float = 3.0
    max_bytes: int = 200_000
    user_agent: str = "Verifiko/1.0"

    def fetch(self, url: str) -> FetchedHtmlDocument | None:
        request = Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": self.user_agent,
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
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
