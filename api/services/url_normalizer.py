from __future__ import annotations

import ipaddress
from urllib.parse import unquote, urlparse, urlunparse

SHORTENER_DOMAINS = {
    "bit.ly",
    "t.co",
    "goo.gl",
    "ow.ly",
    "tinyurl.com",
    "is.gd",
    "buff.ly",
    "tiny.cc",
}


def _is_ipv4_or_ipv6(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_ip_like(host: str) -> bool:
    if not host:
        return False

    if host.isdigit() and len(host) <= 10:
        try:
            val = int(host)
            return 0 <= val <= 2**32 - 1
        except ValueError:
            return False

    if host.lower().startswith("0x"):
        try:
            int(host[2:], 16)
            return True
        except ValueError:
            return False

    return False


def normalize_url(url: str) -> tuple[str, dict]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    p = urlparse(url)

    # Netloc crudo (para detectar userinfo y %encoding)
    raw_netloc = p.netloc or ""
    if "@" in raw_netloc:
        raw_netloc_no_userinfo = raw_netloc.split("@", 1)[1]
    else:
        raw_netloc_no_userinfo = raw_netloc

    metadata = {
        "userinfo_present": bool(p.username or p.password),
        "punycode_present": False,
        "percent_encoded_host": "%" in raw_netloc_no_userinfo,
        "double_encoded": ("%25" in raw_netloc_no_userinfo)
        or ("%25" in (p.path or "")),
        "ip_host": False,
        "ip_like_host": False,
        "shortener": False,
        "original_netloc": p.netloc,
        "original_host": p.hostname or "",
    }

    # Fuente de verdad del host: urlparse ya lo devuelve sin puerto, sin brackets, sin userinfo
    hostname = (p.hostname or "").lower()

    # Si el netloc estaba percent-encoded, intentamos decodificar SOLO para detección adicional
    # (no para construir autoridad “real”)
    decoded_no_userinfo = unquote(raw_netloc_no_userinfo).lower()

    # Si p.hostname fallara por algún caso extremo, intenta rescate sin romper IPv6
    if not hostname and decoded_no_userinfo:
        # Si parece [IPv6] o contiene ':', NO hagas split(':') (es IPv6)
        # Solo remove brackets si existieran
        candidate = decoded_no_userinfo
        if candidate.startswith("[") and "]" in candidate:
            candidate = candidate[1 : candidate.index("]")]
        else:
            # Para host normal, sí podés separar por puerto
            if ":" in candidate:
                candidate = candidate.rsplit(":", 1)[0]
        hostname = candidate.strip()

    if "xn--" in hostname:
        metadata["punycode_present"] = True

    if hostname and _is_ipv4_or_ipv6(hostname):
        metadata["ip_host"] = True

    if hostname and _is_ip_like(hostname):
        metadata["ip_like_host"] = True

    if hostname in SHORTENER_DOMAINS:
        metadata["shortener"] = True

    path = p.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"

    # Reconstruir netloc (sin userinfo). Para IPv6, urlunparse suele requerir brackets.
    # Si es IPv6, lo envolvemos en [].
    netloc_host = hostname
    if metadata["ip_host"] and ":" in hostname:
        netloc_host = f"[{hostname}]"

    netloc = netloc_host
    if p.port:
        netloc = f"{netloc}:{p.port}"

    normalized = urlunparse((p.scheme, netloc, path, "", p.query or "", ""))

    return normalized, metadata
