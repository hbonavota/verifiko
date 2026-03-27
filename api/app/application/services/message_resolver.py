from __future__ import annotations

import re
from typing import Any

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.i18n.resolver import ResolvedSignalText, resolve_message, resolve_signal_text

_KNOWN_WARNING_KEYS = {
    "HTML content fetch was blocked for a private or special-use target.": (
        "warning.html_fetch_blocked_private_target"
    ),
}

_KNOWN_ERROR_KEYS = {
    "Client-supplied signals are not accepted on this endpoint.": (
        "error.client_supplied_signals_not_accepted"
    ),
    "Invalid verification id.": "error.invalid_verification_id",
    "URL input cannot be empty.": "error.url_input_empty",
    "Only HTTP and HTTPS URLs are supported.": "error.only_http_https_urls_supported",
    "URL host is required.": "error.url_host_required",
    "Invalid unicode host name.": "error.invalid_unicode_host_name",
    "Only HTTP and HTTPS outbound targets are allowed.": (
        "error.only_http_https_outbound_targets_allowed"
    ),
    "Outbound target host is required.": "error.outbound_target_host_required",
    "Outbound target is a local or special-use hostname and was blocked.": (
        "error.outbound_target_local_special_use_blocked"
    ),
    "Outbound target uses a single-label hostname and was blocked.": (
        "error.outbound_target_single_label_blocked"
    ),
    "Outbound target resolved to a private or special-use address and was blocked.": (
        "error.outbound_target_private_special_use_address_blocked"
    ),
    "Outbound target host could not be resolved for safety validation.": (
        "error.outbound_target_host_unresolved_for_safety_validation"
    ),
}

_VERIFICATION_NOT_FOUND_RE = re.compile(r"^Verification not found: (?P<verification_id>.+)$")


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


def message_ref(message_key: str, **params: Any) -> dict[str, Any]:
    return {"key": message_key, "params": params}


def normalize_warning_message(
    value: str | None,
    *,
    default_key: str,
    language: str = "en",
) -> str:
    if value:
        message_key = _KNOWN_WARNING_KEYS.get(value)
        if message_key is not None:
            return resolve_message(message_key, language=language)
    return resolve_message(default_key, language=language)


def localize_known_error_message(value: str, *, language: str = "en") -> str:
    verification_not_found = _VERIFICATION_NOT_FOUND_RE.match(value)
    if verification_not_found:
        return resolve_message(
            "error.verification_not_found",
            verification_not_found.groupdict(),
            language=language,
        )

    message_key = _KNOWN_ERROR_KEYS.get(value)
    if message_key is not None:
        return resolve_message(message_key, language=language)

    return value


def normalize_tls_failure_reason(value: str | None) -> str | dict[str, Any] | None:
    if not value:
        return None

    normalized = value.strip().lower()
    if "certificate verify failed" in normalized:
        return message_ref("phrase.tls_reason_certificate_verify_failed")
    if "hostname mismatch" in normalized:
        return message_ref("phrase.tls_reason_hostname_mismatch")
    return value


__all__ = [
    "ResolvedSignalText",
    "build_localized_signal",
    "evidence_ref",
    "localize_known_error_message",
    "message_ref",
    "normalize_warning_message",
    "normalize_tls_failure_reason",
    "resolve_message",
    "resolve_signal_text",
]
