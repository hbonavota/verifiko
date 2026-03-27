from app.application.dto.verification_dto import (
    AnalysisSignalDTO,
    AnalysisStageTraceDTO,
    AnalysisTraceDTO,
    CompoundRuleDeltaDTO,
    ExplanationFactorDTO,
    RiskAssessmentDTO,
    RiskExplanationDTO,
    ScoreBreakdownDTO,
    SignalContributionDTO,
    VerificationDTO,
)
from app.application.services.verification_text_localizer import localize_verification_dto


def test_verification_text_localizer_returns_english_response_unchanged() -> None:
    dto = VerificationDTO(
        id="verification-1",
        target_type="URL",
        original_input="https://fresh-example.test/login",
        normalized_input="https://fresh-example.test/login",
        status="COMPLETED",
        signals=(),
        risk_assessment=None,
        trace=None,
        score_breakdown=None,
        created_at="2026-03-27T10:00:00+00:00",
        updated_at="2026-03-27T10:00:00+00:00",
        completed_at="2026-03-27T10:00:00+00:00",
        calculation_version="v1",
    )

    assert localize_verification_dto(dto, locale="en") is dto


def test_verification_text_localizer_translates_backend_generated_text_to_spanish() -> None:
    signal = AnalysisSignalDTO(
        id="signal-1",
        signal_type="recent_domain_registration",
        category="domain_reputation",
        severity="HIGH",
        confidence=93,
        detected=True,
        title="Very recent domain registration",
        description="The registered domain appears to have been created within the last 7 days.",
        evidence=(
            "Observed domain: fresh-example.test.",
            "Registration date: 2026-03-15.",
            "Computed domain age: 2 day(s).",
            "Lookup provider: stub-rdap.",
        ),
        source="domain-recency-analyzer",
        base_weight=18,
        score_contribution=25.11,
        tags=("domain-age", "registration-recency"),
        created_at="2026-03-27T10:00:00+00:00",
        message_key="signal.very_recent_domain_registration",
        message_params={
            "threshold_days": 7,
            "evidence": [
                {"key": "evidence.observed_domain", "params": {"observed_domain": "fresh-example.test"}},
                {"key": "evidence.registration_date", "params": {"registration_date": "2026-03-15"}},
                {"key": "evidence.computed_domain_age_days", "params": {"age_in_days": 2}},
                {"key": "evidence.lookup_provider", "params": {"provider_name": "stub-rdap"}},
            ],
        },
    )
    stage_trace = AnalysisStageTraceDTO(
        stage="domain_recency",
        source="domain-recency-analyzer",
        status="degraded",
        signal_count=1,
        signal_titles=("Very recent domain registration",),
        warnings=("Domain registration intelligence was unavailable for this run.",),
    )
    explanation = RiskExplanationDTO(
        headline="The engine produced a caution outcome driven by Very recent domain registration.",
        decision_basis="Score 74.89 mapped to low risk. Main contributing categories: domain_reputation=25.11.",
        primary_factors=(
            ExplanationFactorDTO(
                signal_type="recent_domain_registration",
                title="Very recent domain registration",
                source="domain-recency-analyzer",
                severity="HIGH",
                score_contribution=25.11,
                evidence=signal.evidence,
                message_key=signal.message_key,
                message_params=signal.message_params,
            ),
        ),
        analysis_trace=(stage_trace,),
        coverage_warnings=("Domain registration intelligence was unavailable for this run.",),
    )
    assessment = RiskAssessmentDTO(
        score=74.89,
        risk_level="LOW",
        verdict="CAUTION",
        summary="Detected 1 risk signal(s) with low risk output.",
        top_signals=("Very recent domain registration",),
        category_breakdown={"domain_reputation": 25.11},
        terminal_override=False,
        terminal_reason=None,
        calculation_version="v1",
        analysis_warnings=("Domain registration intelligence was unavailable for this run.",),
        analysis_trace=(stage_trace,),
        explanation=explanation,
        calculated_at="2026-03-27T10:00:00+00:00",
    )
    dto = VerificationDTO(
        id="verification-1",
        target_type="URL",
        original_input="https://fresh-example.test/login",
        normalized_input="https://fresh-example.test/login",
        status="COMPLETED",
        signals=(signal,),
        risk_assessment=assessment,
        trace=AnalysisTraceDTO(
            layers_executed=("domain-recency-analyzer",),
            signals_by_source={"domain-recency-analyzer": (signal,)},
            total_signals=1,
        ),
        score_breakdown=ScoreBreakdownDTO(
            base_score=100.0,
            signal_contributions=(
                SignalContributionDTO(
                    signal_type="recent_domain_registration",
                    base_weight=18,
                    confidence=93,
                    impact=25.11,
                ),
            ),
            compound_rules_applied=(),
            final_score=74.89,
        ),
        created_at="2026-03-27T10:00:00+00:00",
        updated_at="2026-03-27T10:00:00+00:00",
        completed_at="2026-03-27T10:00:00+00:00",
        calculation_version="v1",
    )

    localized = localize_verification_dto(dto, locale="es")

    assert localized.signals[0].title == "Registro de dominio muy reciente"
    assert localized.signals[0].description == (
        "El dominio registrado parece haberse creado en los últimos 7 días."
    )
    assert localized.signals[0].evidence == (
        "Dominio observado: fresh-example.test.",
        "Fecha de registro: 2026-03-15.",
        "Antigüedad calculada del dominio: 2 día(s).",
        "Proveedor de consulta: stub-rdap.",
    )
    assert localized.risk_assessment is not None
    assert localized.risk_assessment.summary.startswith("Cobertura del análisis degradada:")
    assert localized.risk_assessment.top_signals == ("Registro de dominio muy reciente",)
    assert localized.risk_assessment.analysis_warnings == (
        "La inteligencia de registro del dominio no estuvo disponible en esta ejecución.",
    )
    assert localized.risk_assessment.explanation.headline.startswith("El motor produjo")
    assert localized.risk_assessment.explanation.primary_factors[0].title == (
        "Registro de dominio muy reciente"
    )
    assert localized.risk_assessment.explanation.coverage_warnings == (
        "La inteligencia de registro del dominio no estuvo disponible en esta ejecución.",
    )
    assert localized.trace is not None
    assert localized.trace.signals_by_source["domain-recency-analyzer"][0].title == (
        "Registro de dominio muy reciente"
    )


def test_verification_text_localizer_summarizes_compound_rules_without_internal_ids() -> None:
    assessment = RiskAssessmentDTO(
        score=98,
        risk_level="SAFE",
        verdict="TRUSTED",
        summary=(
            "Detected 0 risk signal(s) with safe risk output. Category penalties totaled 0.00 and "
            "compound penalties totaled 2.00. Compound pattern adjustments applied: 1."
        ),
        top_signals=(),
        category_breakdown={},
        terminal_override=False,
        terminal_reason=None,
        calculation_version="v1",
        analysis_warnings=(),
        analysis_trace=(),
        explanation=RiskExplanationDTO(
            headline="The engine produced a trusted outcome without high-confidence driver signals.",
            decision_basis="Score 98 mapped to safe risk with no category penalties recorded.",
            primary_factors=(),
            analysis_trace=(),
            coverage_warnings=(),
        ),
        calculated_at="2026-03-27T10:00:00+00:00",
    )
    dto = VerificationDTO(
        id="verification-1",
        target_type="URL",
        original_input="https://unknown-clean.example/",
        normalized_input="https://unknown-clean.example/",
        status="COMPLETED",
        signals=(),
        risk_assessment=assessment,
        trace=None,
        score_breakdown=ScoreBreakdownDTO(
            base_score=100.0,
            signal_contributions=(),
            compound_rules_applied=(
                CompoundRuleDeltaDTO(rule_name="evidence_light_clean_result", delta=2.0),
            ),
            final_score=98.0,
        ),
        created_at="2026-03-27T10:00:00+00:00",
        updated_at="2026-03-27T10:00:00+00:00",
        completed_at="2026-03-27T10:00:00+00:00",
        calculation_version="v1",
    )

    localized = localize_verification_dto(dto, locale="es")

    assert localized.risk_assessment is not None
    assert "Ajustes por patrones compuestos aplicados: 1." in localized.risk_assessment.summary
    assert "evidence_light_clean_result" not in localized.risk_assessment.summary


def test_verification_text_localizer_leads_with_primary_concern_for_risky_results() -> None:
    signal = AnalysisSignalDTO(
        id="signal-brand-1",
        signal_type="brand_impersonation",
        category="content_behavior",
        severity="HIGH",
        confidence=92,
        detected=True,
        title="Institution-style payment or penalty lure",
        description="Government or authority-style payment, traffic, or penalty wording appears on a non-official domain.",
        evidence=("Matched institution terms: traffic.",),
        source="resolved-destination-url-analyzer",
        base_weight=18,
        created_at="2026-03-27T10:00:00+00:00",
        tags=("traffic",),
        score_contribution=24.84,
        message_key="signal.institution_style_payment_or_penalty_lure",
        message_params={
            "evidence": [
                {
                    "key": "evidence.matched_institution_terms",
                    "params": {"terms": "traffic"},
                }
            ]
        },
    )
    assessment = RiskAssessmentDTO(
        score=52,
        risk_level="MEDIUM",
        verdict="SUSPICIOUS",
        summary="Detected 1 risk signal(s) with medium risk output. Category penalties totaled 24.84 and compound penalties totaled 0.00.",
        top_signals=("Institution-style payment or penalty lure",),
        category_breakdown={"content_behavior": 15.0},
        terminal_override=False,
        terminal_reason=None,
        calculation_version="v1",
        analysis_warnings=(),
        analysis_trace=(),
        explanation=RiskExplanationDTO(
            headline="The engine produced a suspicious outcome driven by Institution-style payment or penalty lure.",
            decision_basis="Score 52 mapped to medium risk with category penalties.",
            primary_factors=(),
            analysis_trace=(),
            coverage_warnings=(),
        ),
        calculated_at="2026-03-27T10:00:00+00:00",
    )
    dto = VerificationDTO(
        id="verification-2",
        target_type="URL",
        original_input="https://portal-example.top/pay",
        normalized_input="https://portal-example.top/pay",
        status="COMPLETED",
        signals=(signal,),
        risk_assessment=assessment,
        trace=None,
        score_breakdown=ScoreBreakdownDTO(
            base_score=100.0,
            signal_contributions=(),
            compound_rules_applied=(),
            final_score=52.0,
        ),
        created_at="2026-03-27T10:00:00+00:00",
        updated_at="2026-03-27T10:00:00+00:00",
        completed_at="2026-03-27T10:00:00+00:00",
        calculation_version="v1",
    )

    localized = localize_verification_dto(dto, locale="es")

    assert localized.risk_assessment is not None
    assert localized.risk_assessment.summary.startswith(
        "Principal riesgo: indicios de suplantación de marca o institución."
    )
    assert "También se detectaron otros indicadores de riesgo." not in localized.risk_assessment.summary


def test_verification_text_localizer_translates_nested_tls_failure_reason_params() -> None:
    signal = AnalysisSignalDTO(
        id="signal-tls-1",
        signal_type="tls_validation_failure",
        category="network_transport",
        severity="MEDIUM",
        confidence=84,
        detected=True,
        title="TLS validation failure",
        description="The HTTPS endpoint could not be validated with the system TLS trust store.",
        evidence=(
            "Observed URL scheme: https.",
            "Validated host: portal-example.test.",
            "Validation provider: stub-tls.",
            "TLS failure reason: certificate verify failed.",
        ),
        source="transport-security-analyzer",
        base_weight=18,
        score_contribution=12.0,
        tags=("tls", "transport-security"),
        created_at="2026-03-27T10:00:00+00:00",
        message_key="signal.tls_validation_failure",
        message_params={
            "evidence": [
                {"key": "evidence.observed_url_scheme", "params": {"scheme": "https"}},
                {"key": "evidence.validated_host", "params": {"host": "portal-example.test"}},
                {"key": "evidence.validation_provider", "params": {"provider_name": "stub-tls"}},
                {
                    "key": "evidence.tls_failure_reason",
                    "params": {
                        "failure_reason": {
                            "key": "phrase.tls_reason_certificate_verify_failed",
                            "params": {},
                        }
                    },
                },
            ],
        },
    )
    dto = VerificationDTO(
        id="verification-tls-1",
        target_type="URL",
        original_input="https://portal-example.test/login",
        normalized_input="https://portal-example.test/login",
        status="COMPLETED",
        signals=(signal,),
        risk_assessment=None,
        trace=AnalysisTraceDTO(
            layers_executed=("transport-security-analyzer",),
            signals_by_source={"transport-security-analyzer": (signal,)},
            total_signals=1,
        ),
        score_breakdown=None,
        created_at="2026-03-27T10:00:00+00:00",
        updated_at="2026-03-27T10:00:00+00:00",
        completed_at="2026-03-27T10:00:00+00:00",
        calculation_version="v1",
    )

    localized = localize_verification_dto(dto, locale="es")

    assert localized.signals[0].evidence[3] == (
        "Motivo del fallo TLS: falló la verificación del certificado."
    )
