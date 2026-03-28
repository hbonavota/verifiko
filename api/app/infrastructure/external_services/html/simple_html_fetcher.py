from dataclasses import dataclass

from app.application.ports.html_fetcher import (
    FetchedHtmlDocument,
    HtmlFetchError,
    HtmlFetcherPort,
)
from app.infrastructure.external_services.outbound_target_guard import UnsafeOutboundTargetError
from app.infrastructure.external_services.pinned_http_client import send_pinned_get_request


@dataclass(slots=True)
class SimpleHtmlFetcher(HtmlFetcherPort):
    timeout_seconds: float = 3.0
    max_bytes: int = 200_000
    user_agent: str = "Verifiko/1.0"

    def fetch(self, url: str) -> FetchedHtmlDocument | None:
        try:
            response = send_pinned_get_request(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "User-Agent": self.user_agent,
                },
                timeout_seconds=self.timeout_seconds,
                read_body=True,
                max_bytes=self.max_bytes,
            )
        except UnsafeOutboundTargetError as exc:
            raise HtmlFetchError(
                "HTML content fetch was blocked for a private or special-use target."
            ) from exc
        except (TimeoutError, OSError, UnicodeDecodeError) as exc:
            raise HtmlFetchError(str(exc)) from exc

        if response.status_code >= 400:
            raise HtmlFetchError(f"HTTP Error {response.status_code}")

        content_type = response.headers.get("Content-Type")
        if content_type is not None and "html" not in content_type.lower():
            return None

        encoding = _extract_charset(content_type) or "utf-8"
        content = response.body.decode(encoding, errors="replace")
        return FetchedHtmlDocument(
            content=content,
            source_url=url,
            content_type=content_type,
        )


def _extract_charset(content_type: str | None) -> str | None:
    if content_type is None:
        return None

    for fragment in content_type.split(";")[1:]:
        name, _, value = fragment.partition("=")
        if name.strip().lower() == "charset" and value.strip():
            return value.strip()
    return None
