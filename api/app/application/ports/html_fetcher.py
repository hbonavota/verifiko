from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FetchedHtmlDocument:
    content: str
    source_url: str
    content_type: str | None = None


class HtmlFetchError(Exception):
    """Raised when the target HTML cannot be fetched reliably."""


class HtmlFetcherPort(ABC):
    @abstractmethod
    def fetch(self, url: str) -> FetchedHtmlDocument | None:
        raise NotImplementedError
