from dataclasses import dataclass
import ipaddress
from urllib.parse import SplitResult, unquote, urlsplit, urlunsplit

from app.domain.exceptions.domain_exception import DomainException

_ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}
_MULTI_LABEL_PUBLIC_SUFFIXES = {
    "ac.jp",
    "ac.nz",
    "ac.uk",
    "co.jp",
    "co.nz",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.hk",
    "com.mx",
    "com.my",
    "com.sg",
    "com.tr",
    "com.tw",
    "edu.au",
    "gov.au",
    "gov.uk",
    "govt.nz",
    "ltd.uk",
    "me.uk",
    "net.au",
    "net.uk",
    "ne.jp",
    "or.jp",
    "org.au",
    "org.nz",
    "org.uk",
    "plc.uk",
    "sch.uk",
}


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
    decoded_path: str
    decoded_query: str
    decoded_fragment: str
    registered_domain: str
    subdomain: str
    is_ip_address: bool
    contains_unicode: bool
    contains_punycode: bool
    contains_zero_width_chars: bool
    has_userinfo: bool
    userinfo: str

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
        contains_punycode = any(label.startswith("xn--") for label in ascii_host.split("."))
        has_userinfo = bool(parsed.username or parsed.password)
        registered_domain, subdomain = _extract_domain_parts(ascii_host, is_ip_address)
        decoded_path = _decode_component(parsed.path or "/")
        decoded_query = _decode_component(parsed.query)
        decoded_fragment = _decode_component(parsed.fragment)
        userinfo = ":".join(
            part
            for part in (
                _decode_component(parsed.username or ""),
                _decode_component(parsed.password or ""),
            )
            if part
        )

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
            decoded_path=decoded_path,
            decoded_query=decoded_query,
            decoded_fragment=decoded_fragment,
            registered_domain=registered_domain,
            subdomain=subdomain,
            is_ip_address=is_ip_address,
            contains_unicode=contains_unicode,
            contains_punycode=contains_punycode,
            contains_zero_width_chars=contains_zero_width_chars,
            has_userinfo=has_userinfo,
            userinfo=userinfo,
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

    suffix_length = 2
    candidate_suffix = ".".join(labels[-2:])
    if len(labels) >= 3 and candidate_suffix in _MULTI_LABEL_PUBLIC_SUFFIXES:
        suffix_length = 3

    registered_domain = ".".join(labels[-suffix_length:])
    subdomain = ".".join(labels[:-suffix_length])
    return registered_domain, subdomain


def _decode_component(value: str) -> str:
    decoded = value
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded
