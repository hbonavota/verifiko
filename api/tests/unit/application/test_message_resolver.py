from app.application.services.message_resolver import (
    build_localized_signal,
    evidence_ref,
    localize_known_error_message,
    normalize_tls_failure_reason,
    normalize_warning_message,
    resolve_message,
)
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.value_objects.confidence_score import ConfidenceScore


def test_message_resolver_returns_english_and_spanish_messages() -> None:
    assert (
        resolve_message(
            "warning.domain_registration_unavailable",
            language="en",
        )
        == "Domain registration intelligence was unavailable for this run."
    )
    assert (
        resolve_message(
            "warning.domain_registration_unavailable",
            language="es",
        )
        == "La inteligencia de registro del dominio no estuvo disponible en esta ejecución."
    )


def test_message_resolver_falls_back_to_english_for_unknown_language() -> None:
    assert (
        resolve_message(
            "warning.redirect_resolution_unavailable",
            language="fr",
        )
        == "Redirect resolution could not be completed for this run."
    )


def test_message_resolver_resolves_nested_message_params() -> None:
    assert (
        resolve_message(
            "evidence.tls_failure_reason",
            {
                "failure_reason": {
                    "key": "phrase.tls_reason_certificate_verify_failed",
                    "params": {},
                }
            },
            language="es",
        )
        == "Motivo del fallo TLS: falló la verificación del certificado."
    )


def test_message_resolver_resolves_placeholder_and_pattern_lists() -> None:
    assert (
        resolve_message(
            "evidence.query_parameter_may_steer_navigation",
            {
                "key": "next",
                "value": {"key": "phrase.placeholder_empty_value", "params": {}},
            },
            language="es",
        )
        == "El parámetro de consulta next=(vacío) puede dirigir la navegación."
    )
    assert (
        resolve_message(
            "evidence.matched_infrastructure_patterns",
            {
                "patterns": [
                    {"key": "phrase.infrastructure_pattern_dynamic_dns", "params": {}},
                    {
                        "key": "phrase.infrastructure_pattern_residential_ptr",
                        "params": {},
                    },
                ]
            },
            language="es",
        )
        == "Patrones de infraestructura coincidentes: DNS dinámico, PTR residencial."
    )


def test_build_localized_signal_populates_message_metadata_and_interpolates() -> None:
    signal = build_localized_signal(
        signal_type=SignalType.RECENT_DOMAIN_REGISTRATION,
        category=SignalCategory.DOMAIN_REPUTATION,
        severity=SignalSeverity.HIGH,
        confidence=ConfidenceScore(93),
        source="domain-recency-analyzer",
        base_weight=BASE_SIGNAL_WEIGHTS[SignalType.RECENT_DOMAIN_REGISTRATION],
        message_key="signal.very_recent_domain_registration",
        message_params={
            "threshold_days": 7,
            "evidence": [
                evidence_ref(
                    "evidence.observed_domain", observed_domain="fresh-example.test"
                ),
                evidence_ref("evidence.computed_domain_age_days", age_in_days=2),
            ],
        },
    )

    assert signal.message_key == "signal.very_recent_domain_registration"
    assert signal.message_params["threshold_days"] == 7
    assert signal.title == "Very recent domain registration"
    assert signal.description == (
        "The registered domain appears to have been created within the last 7 days."
    )
    assert signal.evidence == (
        "Observed domain: fresh-example.test.",
        "Computed domain age: 2 day(s).",
    )


def test_normalize_warning_message_prefers_known_catalog_entries() -> None:
    assert (
        normalize_warning_message(
            "HTML content fetch was blocked for a private or special-use target.",
            default_key="warning.html_content_inspection_unavailable",
            language="es",
        )
        == "La obtención del contenido HTML fue bloqueada por apuntar a un destino privado o de uso especial."
    )


def test_normalize_warning_message_falls_back_to_default_key() -> None:
    assert (
        normalize_warning_message(
            "fetch failed for https://example.test/",
            default_key="warning.html_content_inspection_unavailable",
        )
        == "HTML content inspection could not be completed."
    )


def test_localize_known_error_message_translates_known_backend_errors() -> None:
    assert (
        localize_known_error_message(
            "Outbound target uses a single-label hostname and was blocked.",
            language="es",
        )
        == "El destino saliente usa un hostname de una sola etiqueta y fue bloqueado."
    )
    assert (
        localize_known_error_message(
            "Outbound target host could not be resolved for safety validation.",
            language="es",
        )
        == "El host del destino saliente no pudo resolverse para la validación de seguridad."
    )


def test_localize_known_error_message_translates_not_found_with_id() -> None:
    assert (
        localize_known_error_message(
            "Verification not found: 550e8400-e29b-41d4-a716-446655440099",
            language="es",
        )
        == "Verificación no encontrada: 550e8400-e29b-41d4-a716-446655440099"
    )


def test_normalize_tls_failure_reason_maps_known_phrases_to_message_refs() -> None:
    assert normalize_tls_failure_reason("certificate verify failed") == {
        "key": "phrase.tls_reason_certificate_verify_failed",
        "params": {},
    }
    assert normalize_tls_failure_reason(
        "Hostname mismatch, certificate is not valid for foo"
    ) == {
        "key": "phrase.tls_reason_hostname_mismatch",
        "params": {},
    }
