from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.i18n.messages import MESSAGES


@dataclass(frozen=True, slots=True)
class ResolvedSignalText:
    title: str
    description: str
    evidence: tuple[str, ...]


def resolve_message(
    message_key: str,
    message_params: dict[str, Any] | None = None,
    language: str = "en",
) -> str:
    catalog_entry = MESSAGES[message_key]
    selected_language = normalize_language(language)
    params = _resolve_template_params(
        dict(message_params or {}), language=selected_language
    )
    localized = catalog_entry.get(selected_language) or catalog_entry["en"]
    if isinstance(localized, dict):
        raise ValueError(
            f"Message key {message_key} does not resolve to a plain text template."
        )
    return localized.format_map(_FormatMap(params))


def resolve_signal_text(
    message_key: str,
    message_params: dict[str, Any] | None = None,
    language: str = "en",
) -> ResolvedSignalText:
    catalog_entry = MESSAGES[message_key]
    params = dict(message_params or {})
    selected_language = normalize_language(language)
    localized = catalog_entry.get(selected_language) or catalog_entry["en"]
    if not isinstance(localized, dict):
        raise ValueError(
            f"Signal key {message_key} must resolve to a title/description mapping."
        )

    evidence_refs = params.get("evidence") or ()
    evidence = tuple(
        resolve_message(
            ref["key"],
            ref.get("params"),
            language=selected_language,
        )
        for ref in evidence_refs
    )
    template_params = _resolve_template_params(
        {key: value for key, value in params.items() if key != "evidence"},
        language=selected_language,
    )
    return ResolvedSignalText(
        title=localized["title"].format_map(_FormatMap(template_params)),
        description=localized["description"].format_map(_FormatMap(template_params)),
        evidence=evidence,
    )


def normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    normalized = language.lower()
    if normalized.startswith("es"):
        return "es"
    return "en"


class _FormatMap(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _resolve_template_params(
    params: dict[str, Any],
    *,
    language: str,
) -> dict[str, Any]:
    return {
        key: _resolve_template_value(value, language=language)
        for key, value in params.items()
    }


def _resolve_template_value(value: Any, *, language: str) -> Any:
    if isinstance(value, dict):
        if "key" in value and isinstance(value["key"], str):
            return resolve_message(value["key"], value.get("params"), language=language)
        return {
            key: _resolve_template_value(item, language=language)
            for key, item in value.items()
        }
    if isinstance(value, list):
        resolved = [_resolve_template_value(item, language=language) for item in value]
        if all(not isinstance(item, (dict, list, tuple)) for item in resolved):
            return ", ".join(str(item) for item in resolved)
        return resolved
    if isinstance(value, tuple):
        resolved = tuple(
            _resolve_template_value(item, language=language) for item in value
        )
        if all(not isinstance(item, (dict, list, tuple)) for item in resolved):
            return ", ".join(str(item) for item in resolved)
        return resolved
    return value
