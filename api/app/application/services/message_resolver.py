from __future__ import annotations

from typing import Any

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.i18n.resolver import ResolvedSignalText, resolve_message, resolve_signal_text


def build_localized_signal(
    *,
    signal_type,
    category,
    severity,
    confidence,
    source: str,
    base_weight: float,
    message_key: str,
    message_params: dict[str, Any] | None = None,
    detected: bool = True,
    tags: tuple[str, ...] = (),
    language: str = "en",
) -> AnalysisSignal:
    resolved = resolve_signal_text(message_key, message_params, language=language)
    return AnalysisSignal.create(
        signal_type=signal_type,
        category=category,
        severity=severity,
        confidence=confidence,
        title=resolved.title,
        description=resolved.description,
        source=source,
        base_weight=base_weight,
        evidence=resolved.evidence,
        detected=detected,
        tags=tags,
        message_key=message_key,
        message_params=dict(message_params or {}),
    )


def evidence_ref(message_key: str, **params: Any) -> dict[str, Any]:
    return {"key": message_key, "params": params}


__all__ = [
    "ResolvedSignalText",
    "build_localized_signal",
    "evidence_ref",
    "resolve_message",
    "resolve_signal_text",
]
