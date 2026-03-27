from app.application.services.message_resolver import (
    build_localized_signal,
    evidence_ref,
    resolve_message,
)
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.value_objects.confidence_score import ConfidenceScore


def test_message_resolver_returns_english_and_spanish_messages() -> None:
    assert resolve_message(
        "warning.domain_registration_unavailable",
        language="en",
    ) == "Domain registration intelligence was unavailable for this run."
    assert resolve_message(
        "warning.domain_registration_unavailable",
        language="es",
    ) == "La inteligencia de registro del dominio no estuvo disponible en esta ejecución."


def test_message_resolver_falls_back_to_english_for_unknown_language() -> None:
    assert resolve_message(
        "warning.redirect_resolution_unavailable",
        language="fr",
    ) == "Redirect resolution could not be completed for this run."


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
                evidence_ref("evidence.observed_domain", observed_domain="fresh-example.test"),
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
