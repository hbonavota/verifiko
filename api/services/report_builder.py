from __future__ import annotations

from typing import Dict, List, Optional

from .risk_engine import (
    ENGINE_VERSION as DEFAULT_ENGINE_VERSION,
)
from .risk_engine import (
    RULESET_VERSION as DEFAULT_RULESET_VERSION,
)


def build_report(
    signals: List[Dict],
    score: int,
    verdict: str,
    raw_flags: Optional[List[str]] = None,
    derived_signals: Optional[List[str]] = None,
    engine_version: Optional[str] = None,
    ruleset_version: Optional[str] = None,
) -> Dict[str, str]:
    """
    Construye el reporte manteniendo el contrato actual:
      retorna dict con keys: summary, recommendations, confidence_notes (strings)

    Firma extendida para aceptar raw_flags/derived_signals y versiones sin romper llamadas previas.
    """
    raw_flags = raw_flags or []
    derived_signals = derived_signals or []
    engine_version = engine_version or DEFAULT_ENGINE_VERSION
    ruleset_version = ruleset_version or DEFAULT_RULESET_VERSION

    # Summary / recommendations (mantener comportamiento previo)
    if score >= 60:
        summary = f"Alto riesgo detectado (score={score})."
        recommendations = "No ingresar credenciales. Evitar interacción con la URL."
    elif score >= 20:
        summary = f"Riesgo moderado detectado (score={score})."
        recommendations = "Revisar antes de acceder."
    else:
        summary = f"Riesgo bajo (score={score})."
        recommendations = "Parece seguro, siempre precaución."

    # Confidence notes: incluir conteos + versiones
    confidence_notes = (
        f"raw_flags_count={len(raw_flags)} "
        f"derived_signals_count={len(derived_signals)} "
        f"engine={engine_version} ruleset={ruleset_version}"
    )

    return {
        "summary": summary,
        "recommendations": recommendations,
        "confidence_notes": confidence_notes,
    }
