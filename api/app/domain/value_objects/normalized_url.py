from dataclasses import dataclass
import ipaddress
from urllib.parse import SplitResult, urlsplit, urlunsplit

from app.domain.exceptions.domain_exception import DomainException

_ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}


@dataclass(frozen=True, slots=True)
class NormalizedUrl:
    raw: str
    normalized: str
    scheme: str
    host: str
    ascii_host: str
    port: int | None
    path: str
    query: str
    fragment: str
    registered_domain: str
    subdomain: str
    is_ip_address: bool
    contains_unicode: bool
    contains_zero_width_chars: bool

    @staticmethod
    def from_raw(raw_url: str) -> "NormalizedUrl":
        candidate = raw_url.strip()
        if not candidate:
            raise DomainException("URL input cannot be empty.")

        if "//" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlsplit(candidate)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise DomainException("Only HTTP and HTTPS URLs are supported.")
        if not parsed.hostname:
            raise DomainException("URL host is required.")

        host = parsed.hostname.lower().rstrip(".")
        contains_unicode = any(ord(char) > 127 for char in host)
        contains_zero_width_chars = any(char in _ZERO_WIDTH_CHARS for char in host)

        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise DomainException("Invalid unicode host name.") from exc

        is_ip_address = _is_ip_address(ascii_host)
        registered_domain, subdomain = _extract_domain_parts(ascii_host, is_ip_address)

        normalized = _build_normalized_url(parsed, ascii_host)

        return NormalizedUrl(
            raw=raw_url,
            normalized=normalized,
            scheme=parsed.scheme.lower(),
            host=host,
            ascii_host=ascii_host,
            port=parsed.port,
            path=parsed.path or "/",
            query=parsed.query,
            fragment=parsed.fragment,
            registered_domain=registered_domain,
            subdomain=subdomain,
            is_ip_address=is_ip_address,
            contains_unicode=contains_unicode,
            contains_zero_width_chars=contains_zero_width_chars,
        )


def _build_normalized_url(parsed: SplitResult, ascii_host: str) -> str:
    scheme = parsed.scheme.lower()
    path = parsed.path or "/"
    netloc = ascii_host

    if parsed.port is not None:
        netloc = f"{ascii_host}:{parsed.port}"

    return urlunsplit((scheme, netloc, path, parsed.query, parsed.fragment))


def _is_ip_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _extract_domain_parts(host: str, is_ip_address: bool) -> tuple[str, str]:
    if is_ip_address:
        return host, ""

    labels = host.split(".")
    if len(labels) < 2:
        return host, ""

    registered_domain = ".".join(labels[-2:])
    subdomain = ".".join(labels[:-2])
    return registered_domain, subdomain
