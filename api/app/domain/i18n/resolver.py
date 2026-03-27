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
    params = dict(message_params or {})
    selected_language = normalize_language(language)
    localized = catalog_entry.get(selected_language) or catalog_entry["en"]
    if isinstance(localized, dict):
        raise ValueError(f"Message key {message_key} does not resolve to a plain text template.")
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
        raise ValueError(f"Signal key {message_key} must resolve to a title/description mapping.")

    evidence_refs = params.get("evidence") or ()
    evidence = tuple(
        resolve_message(
            ref["key"],
            ref.get("params"),
            language=selected_language,
        )
        for ref in evidence_refs
    )
    return ResolvedSignalText(
        title=localized["title"].format_map(_FormatMap(params)),
        description=localized["description"].format_map(_FormatMap(params)),
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
