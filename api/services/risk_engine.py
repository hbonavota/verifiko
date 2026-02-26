from __future__ import annotations

from typing import List, Set, Tuple
from urllib.parse import urlparse

# Versioning constants
ENGINE_VERSION = "0.4.0"
RULESET_VERSION = "2026-02-25-p0p1"

# Set público de raw flags para clasificar señales guardadas
RAW_FLAG_NAMES: Set[str] = {
    "userinfo_present",
    "punycode_present",
    "percent_encoded_host",
    "double_encoded",
    "ip_host",
    "ip_like_host",
    "shortener_detected",
}


def compute_url_risk(
    normalized_url: str, metadata: dict
) -> Tuple[int, List[str], List[str]]:
    """
    Calcula el score a partir de normalized_url y metadata (raw_flags).
    Retorna siempre (score:int, raw_flags:list[str], derived_signals:list[str])
    """
    # Mapear flags internas a nombres públicos
    raw_flag_map = {
        "userinfo_present": "userinfo_present",
        "punycode_present": "punycode_present",
        "percent_encoded_host": "percent_encoded_host",
        "double_encoded": "double_encoded",
        "ip_host": "ip_host",
        "ip_like_host": "ip_like_host",
        # normalizer usa "shortener" internamente
        "shortener": "shortener_detected",
    }

    # raw_flags: solo las verdaderas
    raw_flags: List[str] = [
        public for k, public in raw_flag_map.items() if metadata.get(k)
    ]

    # Derived signals (heurísticas)
    derived_signals: List[str] = []
    hostname = (metadata.get("original_host") or "").lower()

    # Obtener path desde normalized_url (más fiable)
    parsed = urlparse(normalized_url or "")
    path = (parsed.path or "").lower()

    if hostname:
        labels = [label for label in hostname.split(".") if label]
        # many_subdomains: >= 4 labels (ajuste solicitado)
        if len(labels) >= 4:
            derived_signals.append("many_subdomains")
        if len(hostname) > 35:
            derived_signals.append("long_hostname")

    # brand keyword detection (hostname + path)
    BRANDS = {"paypal", "bank", "google", "amazon", "login"}
    combined = f"{hostname} {path}"
    if any(b in combined for b in BRANDS):
        derived_signals.append("brand_keyword_in_host_or_path")

    # Weights (mantener compatibilidad)
    WEIGHTS = {
        "userinfo_present": 40,
        "punycode_present": 45,
        "percent_encoded_host": 25,
        "double_encoded": 30,
        "ip_host": 30,
        "ip_like_host": 20,
        "shortener_detected": 20,
        "long_hostname": 20,
        "many_subdomains": 15,
        "brand_keyword_in_host_or_path": 20,
    }

    # Calcular score sumando pesos (raw + derived)
    score = 0
    for s in raw_flags + derived_signals:
        score += WEIGHTS.get(s, 0)

    # Gates críticos
    if "userinfo_present" in raw_flags:
        score = max(score, 70)
    if (
        "punycode_present" in raw_flags
        and "brand_keyword_in_host_or_path" in derived_signals
    ):
        score = max(score, 70)
    if "shortener_detected" in raw_flags:
        score = max(score, 35)

    # Clamp final 0..100
    score = max(0, min(100, int(score)))

    return score, raw_flags, derived_signals


def verdict_from_score(score: int) -> str:
    """
    Devuelve veredicto según score.
    Umbrales compatibles con existente:
      - GREEN: < 20
      - YELLOW: 20-59
      - RED: >= 60
    """
    if score >= 60:
        return "🔴 ROJO"
    elif score >= 20:
        return "🟡 AMARILLO"
    else:
        return "🟢 VERDE"
