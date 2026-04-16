from dataclasses import replace
import re
from typing import Literal

from app.application.dto.verification_dto import (
    AnalysisSignalDTO,
    AnalysisStageTraceDTO,
    AnalysisTraceDTO,
    ExplanationFactorDTO,
    RiskAssessmentDTO,
    RiskExplanationDTO,
    ScoreBreakdownDTO,
    VerificationDTO,
)
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.i18n.resolver import resolve_message, resolve_signal_text

SupportedLocale = Literal["en", "es"]

_TITLE_ES = {
    "Direct IP address target": "Destino directo por dirección IP",
    "Unicode or punycode hostname pattern": "Patrón de hostname con Unicode o punycode",
    "Invisible hostname characters": "Caracteres invisibles en el hostname",
    "Non-standard port usage": "Uso de puerto no estándar",
    "Shortened destination": "Destino acortado",
    "Redirect-style parameters": "Parámetros con patrón de redirección",
    "Credential-lure wording in URL": "Cebo de credenciales en la URL",
    "Brand-like impersonation hints": "Indicios de suplantación de marca",
    "Institution-style payment or penalty lure": "Cebo institucional de pago o sanción",
    "Mailbox access lure pattern": "Patrón de cebo de acceso al correo",
    "Deceptive brand-in-subdomain pattern": "Patrón engañoso de marca en subdominio",
    "Misleading subdomain structure": "Estructura de subdominio engañosa",
    "High-entropy hostname token": "Token de hostname con alta entropía",
    "Brand-like domain on uncommon TLD": "Dominio con apariencia de marca en un TLD inusual",
    "Recognized reputable domain": "Dominio reputado reconocido",
    "Very recent domain registration": "Registro de dominio muy reciente",
    "Recent domain registration": "Registro de dominio reciente",
    "Observed redirect chain": "Cadena de redirecciones observada",
    "Credential capture form detected": "Formulario de captura de credenciales detectado",
    "Suspicious login-style interface": "Interfaz de inicio de sesión sospechosa",
    "Parked or placeholder landing page": "Página de aterrizaje aparcada o provisional",
    "Low-information landing page": "Página de aterrizaje con poca información",
    "Insecure transport scheme": "Esquema de transporte inseguro",
    "TLS validation failure": "Fallo de validación TLS",
    "Reputation blacklist match": "Coincidencia en lista negra de reputación",
    "Suspicious infrastructure pattern": "Patrón de infraestructura sospechoso",
}

_DESCRIPTION_ES = {
    "The input targets an IP address directly instead of a named host.": (
        "La entrada apunta directamente a una dirección IP en lugar de a un host con nombre."
    ),
    "The hostname contains unicode characters or punycode labels that merit homograph review.": (
        "El hostname contiene caracteres Unicode o etiquetas punycode que requieren revisión de homógrafos."
    ),
    "Zero-width characters were found in the hostname representation.": (
        "Se encontraron caracteres de ancho cero en la representación del hostname."
    ),
    "The URL uses a non-standard web port, which increases handling risk.": (
        "La URL utiliza un puerto web no estándar, lo que aumenta el riesgo de manejo."
    ),
    "The URL uses a known shortening service that obscures the eventual destination.": (
        "La URL utiliza un servicio de acortamiento conocido que oculta el destino final."
    ),
    "The URL contains redirect-style routing hints that can conceal the final destination.": (
        "La URL contiene indicios de redirección que pueden ocultar el destino final."
    ),
    "The host or path contains account and verification language commonly used in phishing lures.": (
        "El host o la ruta contienen lenguaje de cuenta y verificación usado habitualmente en cebos de phishing."
    ),
    "Brand references are combined with account-action language in a non-official domain.": (
        "Las referencias de marca se combinan con lenguaje de acción sobre la cuenta en un dominio no oficial."
    ),
    "Government or authority-style payment, traffic, or penalty wording appears on a non-official domain.": (
        "Aparece lenguaje de pago, tráfico o sanciones con apariencia gubernamental o institucional en un dominio no oficial."
    ),
    "The URL combines mailbox-style terms with account-action cues.": (
        "La URL combina términos de buzón de correo con indicios de acciones sobre la cuenta."
    ),
    "The subdomain embeds a brand-like domain fragment before the actual registered domain.": (
        "El subdominio incrusta un fragmento con apariencia de marca antes del dominio registrado real."
    ),
    "The subdomain structure adds unusual depth or trust-signaling lure wording ahead of the registered domain.": (
        "La estructura del subdominio añade una profundidad inusual o lenguaje de señuelo que transmite confianza antes del dominio registrado."
    ),
    "One hostname label appears algorithmically generated or unusually noisy.": (
        "Una etiqueta del hostname parece generada algorítmicamente o inusualmente ruidosa."
    ),
    "The hostname mixes brand or account language with a higher-risk TLD choice.": (
        "El hostname mezcla lenguaje de marca o cuenta con un TLD de mayor riesgo."
    ),
    "The registered domain matches a conservative curated set of widely used reputable destinations.": (
        "El dominio registrado coincide con un conjunto conservador y curado de destinos reputados y ampliamente utilizados."
    ),
    "The registered domain appears to have been created within the last 7 days.": (
        "El dominio registrado parece haberse creado en los últimos 7 días."
    ),
    "The registered domain appears to have been created within the last 30 days.": (
        "El dominio registrado parece haberse creado en los últimos 30 días."
    ),
    "The submitted URL resolved through one or more redirects before reaching its final destination.": (
        "La URL enviada se resolvió mediante una o más redirecciones antes de alcanzar su destino final."
    ),
    "The fetched HTML contains a form pattern consistent with credential collection.": (
        "El HTML recuperado contiene un patrón de formulario coherente con la recopilación de credenciales."
    ),
    "The fetched HTML exposes login-style wording and input hints that merit credential-harvesting review.": (
        "El HTML recuperado expone lenguaje de inicio de sesión e indicios de entrada que requieren revisión por posible captura de credenciales."
    ),
    "The fetched HTML looks like a parked domain, default hosting page, or placeholder landing page.": (
        "El HTML recuperado parece corresponder a un dominio aparcado, una página por defecto del hosting o una página provisional."
    ),
    "The fetched HTML contains almost no meaningful visible content, which limits confidence in a clean result.": (
        "El HTML recuperado contiene muy poco contenido visible con significado, lo que limita la confianza en un resultado limpio."
    ),
    "The target uses plain HTTP without TLS protection.": (
        "El destino utiliza HTTP en claro sin protección TLS."
    ),
    "The target uses plain HTTP despite exposing login-oriented or brand-sensitive cues.": (
        "El destino utiliza HTTP en claro a pesar de exponer indicios orientados a inicio de sesión o sensibles para la marca."
    ),
    "The HTTPS endpoint could not be validated with the system TLS trust store.": (
        "El endpoint HTTPS no pudo validarse con el almacén de confianza TLS del sistema."
    ),
    "The target or a resolved redirect destination matched external malicious URL reputation intelligence.": (
        "El destino o un destino final resuelto por redirección coincidió con inteligencia externa de reputación maliciosa."
    ),
    "The effective target resolves to infrastructure with reverse-DNS patterns consistent with disposable, dynamic, or residential hosting.": (
        "El destino efectivo resuelve a una infraestructura con patrones de DNS inverso coherentes con alojamiento desechable, dinámico o residencial."
    ),
}

_WARNING_ES = {
    "Domain registration intelligence was unavailable for this run.": (
        "La inteligencia de registro del dominio no estuvo disponible en esta ejecución."
    ),
    "Redirect resolution could not be completed for this run.": (
        "La resolución de redirecciones no pudo completarse en esta ejecución."
    ),
    "Blacklist reputation intelligence was unavailable for this run.": (
        "La inteligencia de reputación de listas negras no estuvo disponible en esta ejecución."
    ),
    "Infrastructure intelligence could not be completed for this run.": (
        "La inteligencia de infraestructura no pudo completarse en esta ejecución."
    ),
    "TLS validation could not be completed for this run.": (
        "La validación TLS no pudo completarse en esta ejecución."
    ),
    "HTML content inspection could not be completed.": (
        "La inspección del contenido HTML no pudo completarse."
    ),
    "HTML content fetch was blocked for a private or special-use target.": (
        "La obtención del contenido HTML fue bloqueada por apuntar a un destino privado o de uso especial."
    ),
    "Resolved destination HTML inspection could not be completed.": (
        "La inspección HTML del destino resuelto no pudo completarse."
    ),
}

_CATEGORY_ES = {
    "domain_reputation": "reputación del dominio",
    "domain_structure": "estructura del dominio",
    "network_transport": "transporte de red",
    "navigation_behavior": "comportamiento de navegación",
    "content_behavior": "comportamiento del contenido",
}

_VERDICT_LOWER_ES = {
    "TRUSTED": "confiable",
    "CAUTION": "con cautela",
    "SUSPICIOUS": "sospechoso",
    "LIKELY_MALICIOUS": "probablemente malicioso",
    "CONFIRMED_MALICIOUS": "malicioso confirmado",
}

_RISK_LEVEL_LOWER_ES = {
    "SAFE": "seguro",
    "LOW": "bajo",
    "MEDIUM": "medio",
    "HIGH": "alto",
    "CRITICAL": "crítico",
}
_DOMINANT_SUMMARY_CATEGORIES = {
    SignalCategory.NAVIGATION_BEHAVIOR.value,
    SignalCategory.CONTENT_BEHAVIOR.value,
    SignalCategory.DOMAIN_REPUTATION.value,
    SignalCategory.NETWORK_TRANSPORT.value,
}
_DOMINANT_SUMMARY_REASON_KEYS = {
    SignalType.SUSPICIOUS_REDIRECT_CHAIN.value: "summary.reason.suspicious_redirect_chain",
    SignalType.LOW_INFORMATION_PAGE.value: "summary.reason.low_information_page",
    SignalType.CREDENTIAL_HARVEST_FORM.value: "summary.reason.credential_harvest_form",
    SignalType.SUSPICIOUS_LOGIN_INTERFACE.value: "summary.reason.suspicious_login_interface",
    SignalType.TLS_VALIDATION_FAILURE.value: "summary.reason.tls_validation_failure",
    SignalType.INSECURE_TRANSPORT.value: "summary.reason.insecure_transport",
    SignalType.BRAND_IMPERSONATION.value: "summary.reason.brand_impersonation",
    SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN.value: "summary.reason.suspicious_infrastructure_pattern",
}
_DOMINANT_EXPLANATION_CATEGORIES = _DOMINANT_SUMMARY_CATEGORIES
_DOMINANT_EXPLANATION_REASON_KEYS = _DOMINANT_SUMMARY_REASON_KEYS

_EVIDENCE_REGEX_ES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^Host resolves to raw IP (.+)\.$"), "El host apunta directamente a la IP {0}."),
    (re.compile(r"^Rendered host: (.+)\.$"), "Host mostrado: {0}."),
    (
        re.compile(r"^ASCII host contains punycode label\(s\): (.+)\.$"),
        "El host ASCII contiene etiquetas punycode: {0}.",
    ),
    (re.compile(r"^ASCII host: (.+)\.$"), "Host ASCII: {0}."),
    (
        re.compile(r"^Host contains zero-width characters: (.+)\.$"),
        "El host contiene caracteres de ancho cero: {0}.",
    ),
    (re.compile(r"^Observed explicit port (.+)\.$"), "Puerto explícito observado: {0}."),
    (
        re.compile(r"^Registered domain (.+) is a shortener\.$"),
        "El dominio registrado {0} es un acortador.",
    ),
    (
        re.compile(r"^Path contains redirect-style token\(s\): (.+)\.$"),
        "La ruta contiene tokens de redirección: {0}.",
    ),
    (
        re.compile(r"^Query parameter (.+?)=(.*) may steer navigation\.$"),
        "El parámetro de consulta {0}={1} puede dirigir la navegación.",
    ),
    (
        re.compile(r"^Query parameter (.+) embeds a nested URL destination\.$"),
        "El parámetro de consulta {0} incrusta un destino URL anidado.",
    ),
    (re.compile(r"^Matched URL keywords: (.+)\.$"), "Palabras clave de URL coincidentes: {0}."),
    (re.compile(r"^Matched brand terms: (.+)\.$"), "Términos de marca coincidentes: {0}."),
    (
        re.compile(r"^Registered domain under review: (.+)\.$"),
        "Dominio registrado bajo revisión: {0}.",
    ),
    (
        re.compile(r"^Matched institution terms: (.+)\.$"),
        "Términos institucionales coincidentes: {0}.",
    ),
    (re.compile(r"^Matched demand terms: (.+)\.$"), "Términos de exigencia coincidentes: {0}."),
    (re.compile(r"^Matched mailbox terms: (.+)\.$"), "Términos de buzón coincidentes: {0}."),
    (
        re.compile(r"^Observed deceptive fragment: (.+)\.$"),
        "Fragmento engañoso observado: {0}.",
    ),
    (
        re.compile(r"^Registered domain observed: (.+)\.$"),
        "Dominio registrado observado: {0}.",
    ),
    (re.compile(r"^Subdomain observed: (.+)\.$"), "Subdominio observado: {0}."),
    (re.compile(r"^Suspicious label: (.+)\.$"), "Etiqueta sospechosa: {0}."),
    (re.compile(r"^Observed TLD: (.+)\.$"), "TLD observado: {0}."),
    (re.compile(r"^Observed domain: (.+)\.$"), "Dominio observado: {0}."),
    (re.compile(r"^Registration date: (.+)\.$"), "Fecha de registro: {0}."),
    (re.compile(r"^Computed domain age: (\d+) day\(s\)\.$"), "Antigüedad calculada del dominio: {0} día(s)."),
    (re.compile(r"^Lookup provider: (.+)\.$"), "Proveedor de consulta: {0}."),
    (re.compile(r"^Redirect hops observed: (\d+)\.$"), "Saltos de redirección observados: {0}."),
    (
        re.compile(r"^Final URL after redirects: (.+)\.$"),
        "URL final tras las redirecciones: {0}.",
    ),
    (re.compile(r"^Redirect resolver: (.+)\.$"), "Resolvedor de redirecciones: {0}."),
    (
        re.compile(r"^Redirect chain crossed registered domains: (.+)\.$"),
        "La cadena de redirección cruzó dominios registrados: {0}.",
    ),
    (
        re.compile(r"^Redirect chain downgraded transport from HTTPS to HTTP\.$"),
        "La cadena de redirección degradó el transporte de HTTPS a HTTP.",
    ),
    (re.compile(r"^Listed value: (.+)\.$"), "Valor listado: {0}."),
    (re.compile(r"^Reputation provider: (.+)\.$"), "Proveedor de reputación: {0}."),
    (re.compile(r"^Provider references: (\d+)\.$"), "Referencias del proveedor: {0}."),
    (
        re.compile(r"^URLhaus returned (\d+) malicious URL record\(s\) for the queried host\.$"),
        "URLhaus devolvió {0} registro(s) de URL maliciosa para el host consultado.",
    ),
    (re.compile(r"^Final redirect target: (.+)\.$"), "Destino final de la redirección: {0}."),
    (re.compile(r"^Effective target host: (.+)\.$"), "Host del destino efectivo: {0}."),
    (re.compile(r"^Infrastructure provider: (.+)\.$"), "Proveedor de infraestructura: {0}."),
    (re.compile(r"^Resolved addresses: (.+)\.$"), "Direcciones resueltas: {0}."),
    (
        re.compile(r"^Matched infrastructure patterns: (.+)\.$"),
        "Patrones de infraestructura coincidentes: {0}.",
    ),
    (re.compile(r"^Reverse DNS sample: (.+)\.$"), "Muestra de DNS inverso: {0}."),
    (
        re.compile(r"^Matched sensitive URL terms: (.+)\.$"),
        "Términos sensibles de URL coincidentes: {0}.",
    ),
    (
        re.compile(r"^Effective target derived from redirect chain: (.+)\.$"),
        "Destino efectivo derivado de la cadena de redirección: {0}.",
    ),
    (re.compile(r"^Observed URL scheme: (.+)\.$"), "Esquema URL observado: {0}."),
    (re.compile(r"^Observed host: (.+)\.$"), "Host observado: {0}."),
    (re.compile(r"^Validated host: (.+)\.$"), "Host validado: {0}."),
    (re.compile(r"^Validation provider: (.+)\.$"), "Proveedor de validación: {0}."),
    (re.compile(r"^TLS failure reason: (.+)\.$"), "Motivo del fallo TLS: {0}."),
    (re.compile(r"^HTML forms found: (\d+)\.$"), "Formularios HTML encontrados: {0}."),
    (re.compile(r"^Password fields found: (\d+)\.$"), "Campos de contraseña encontrados: {0}."),
    (
        re.compile(r"^Matched account input hints: (.+)\.$"),
        "Indicadores coincidentes de campos de cuenta: {0}.",
    ),
    (
        re.compile(r"^Matched login wording: (.+)\.$"),
        "Texto coincidente de inicio de sesión: {0}.",
    ),
    (re.compile(r"^Observed form action: (.+)\.$"), "Acción de formulario observada: {0}."),
    (
        re.compile(r"^Suspicious form action: (.+)\.$"),
        "Acción de formulario sospechosa: {0}.",
    ),
    (re.compile(r"^Visible text tokens found: (\d+)\.$"), "Tokens de texto visible encontrados: {0}."),
    (
        re.compile(r"^Matched placeholder markers: (.+)\.$"),
        "Marcadores coincidentes de página provisional: {0}.",
    ),
    (re.compile(r"^Resolved final URL: (.+)\.$"), "URL final resuelta: {0}."),
)

_EVIDENCE_EXACT_ES = {
    "The fetched landing page exposes no forms or meaningful visible copy.": (
        "La página de aterrizaje recuperada no expone formularios ni contenido visible con significado."
    ),
}


def localize_verification_dto(
    verification: VerificationDTO,
    locale: SupportedLocale = "en",
) -> VerificationDTO:
    if locale == "en":
        return verification

    localized_signals = tuple(_localize_signal(signal) for signal in verification.signals)
    localized_signals_by_id = {signal.id: signal for signal in localized_signals}
    localized_trace = _localize_trace(verification.trace, localized_signals_by_id)
    localized_assessment = _localize_assessment(
        verification.risk_assessment,
        localized_signals,
        verification.score_breakdown,
    )

    return replace(
        verification,
        signals=localized_signals,
        risk_assessment=localized_assessment,
        trace=localized_trace,
    )


def _localize_trace(
    trace: AnalysisTraceDTO | None,
    localized_signals_by_id: dict[str, AnalysisSignalDTO],
) -> AnalysisTraceDTO | None:
    if trace is None:
        return None

    signals_by_source = {
        source: tuple(
            localized_signals_by_id.get(signal.id, _localize_signal(signal))
            for signal in signals
        )
        for source, signals in trace.signals_by_source.items()
    }

    return replace(trace, signals_by_source=signals_by_source)


def _localize_assessment(
    assessment: RiskAssessmentDTO | None,
    localized_signals: tuple[AnalysisSignalDTO, ...],
    score_breakdown: ScoreBreakdownDTO | None,
) -> RiskAssessmentDTO | None:
    if assessment is None:
        return None

    localized_analysis_warnings = tuple(_localize_warning(item) for item in assessment.analysis_warnings)
    localized_analysis_trace = tuple(
        _localize_stage_trace(stage) for stage in assessment.analysis_trace
    )
    localized_top_signals = tuple(_localize_title(item) for item in assessment.top_signals)
    localized_explanation = _localize_explanation(
        assessment,
        assessment.explanation,
        localized_signals,
    )

    return replace(
        assessment,
        summary=assessment.summary,
        top_signals=localized_top_signals,
        analysis_warnings=localized_analysis_warnings,
        analysis_trace=localized_analysis_trace,
        explanation=localized_explanation,
    )


def _localize_explanation(
    assessment: RiskAssessmentDTO,
    explanation: RiskExplanationDTO,
    localized_signals: tuple[AnalysisSignalDTO, ...],
) -> RiskExplanationDTO:
    localized_primary_factors = tuple(
        _localize_factor(factor)
        for factor in explanation.primary_factors
    )
    localized_trace = tuple(_localize_stage_trace(stage) for stage in explanation.analysis_trace)
    localized_coverage_warnings = tuple(_localize_warning(item) for item in explanation.coverage_warnings)

    return replace(
        explanation,
        headline=_build_spanish_headline(
            assessment,
            localized_primary_factors,
            localized_signals,
        ),
        decision_basis=_build_spanish_decision_basis(
            assessment,
            localized_primary_factors,
            localized_signals,
        ),
        primary_factors=localized_primary_factors,
        analysis_trace=localized_trace,
        coverage_warnings=localized_coverage_warnings,
    )


def _localize_stage_trace(stage: AnalysisStageTraceDTO) -> AnalysisStageTraceDTO:
    return replace(
        stage,
        signal_titles=tuple(_localize_title(item) for item in stage.signal_titles),
        warnings=tuple(_localize_warning(item) for item in stage.warnings),
    )


def _localize_signal(signal: AnalysisSignalDTO) -> AnalysisSignalDTO:
    if signal.message_key:
        resolved = resolve_signal_text(
            signal.message_key,
            signal.message_params,
            language="es",
        )
        return replace(
            signal,
            title=resolved.title,
            description=resolved.description,
            evidence=resolved.evidence,
        )

    return replace(
        signal,
        title=_localize_title(signal.title),
        description=_localize_description(signal.description),
        evidence=tuple(_localize_evidence(item) for item in signal.evidence),
    )


def _localize_factor(factor: ExplanationFactorDTO) -> ExplanationFactorDTO:
    if factor.message_key:
        resolved = resolve_signal_text(
            factor.message_key,
            factor.message_params,
            language="es",
        )
        return replace(
            factor,
            title=resolved.title,
            evidence=resolved.evidence,
        )
    return replace(
        factor,
        title=_localize_title(factor.title),
        evidence=tuple(_localize_evidence(item) for item in factor.evidence),
    )


def _build_spanish_summary(
    assessment: RiskAssessmentDTO,
    localized_signals: tuple[AnalysisSignalDTO, ...],
    localized_analysis_warnings: tuple[str, ...],
    score_breakdown: ScoreBreakdownDTO | None,
) -> str:
    if assessment.terminal_override:
        summary = resolve_message("summary.terminal_blacklist_override", language="es")
    else:
        risk_signals = [
            signal for signal in localized_signals if signal.detected and signal.score_contribution > 0
        ]
        informational_signals = [
            signal for signal in localized_signals if signal.detected and signal.score_contribution == 0
        ]
        category_total_penalty = sum(assessment.category_breakdown.values())
        compound_penalty = sum(
            entry.delta
            for entry in (score_breakdown.compound_rules_applied if score_breakdown else ())
        )
        summary = resolve_message(
            "summary.risk_detected",
            {
                "risk_signal_count": len(risk_signals),
                "risk_level": _risk_level_lower(assessment.risk_level),
                "category_total_penalty": category_total_penalty,
                "compound_penalty": compound_penalty,
            },
            language="es",
        )

        dominant_signal = _select_dominant_summary_signal_dto(risk_signals)
        if dominant_signal:
            summary = resolve_message(
                "summary.primary_concern",
                {
                    "summary": summary,
                    "reason": resolve_message(
                        _DOMINANT_SUMMARY_REASON_KEYS[dominant_signal.signal_type],
                        language="es",
                    ),
                },
                language="es",
            )
            if len(risk_signals) > 1:
                summary = resolve_message(
                    "summary.secondary_factors",
                    {"summary": summary},
                    language="es",
                )

        if score_breakdown and score_breakdown.compound_rules_applied:
            summary = resolve_message(
                "summary.rules",
                {
                    "summary": summary,
                    "rule_count": len(score_breakdown.compound_rules_applied),
                },
                language="es",
            )

        if informational_signals:
            summary = resolve_message(
                "summary.supporting_trust_context",
                {
                    "summary": summary,
                    "trust_context": ", ".join(signal.title for signal in informational_signals[:2]),
                },
                language="es",
            )

    if localized_analysis_warnings:
        summary = resolve_message(
            "summary.analysis_coverage_degraded",
            {
                "warnings": " ".join(localized_analysis_warnings),
                "summary": summary,
            },
            language="es",
        )

    return summary


def _select_dominant_summary_signal_dto(
    signals: list[AnalysisSignalDTO],
) -> AnalysisSignalDTO | None:
    eligible = [
        signal
        for signal in signals
        if signal.severity in {SignalSeverity.HIGH.value, SignalSeverity.CRITICAL.value}
        and signal.confidence > 80
        and signal.category in _DOMINANT_SUMMARY_CATEGORIES
        and signal.signal_type in _DOMINANT_SUMMARY_REASON_KEYS
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda signal: signal.score_contribution)


def _build_spanish_headline(
    assessment: RiskAssessmentDTO,
    primary_factors: tuple[ExplanationFactorDTO, ...],
    localized_signals: tuple[AnalysisSignalDTO, ...],
) -> str:
    if assessment.terminal_override:
        return resolve_message("explanation.headline.terminal_override", language="es")
    dominant_signal = _select_dominant_explanation_signal_dto(localized_signals)
    if dominant_signal is not None and assessment.risk_level != "SAFE":
        return resolve_message(
            "explanation.headline.primary_concern",
            {
                "verdict": _verdict_lower(assessment.verdict),
                "reason": resolve_message(
                    _DOMINANT_EXPLANATION_REASON_KEYS[dominant_signal.signal_type],
                    language="es",
                ),
            },
            language="es",
        )

    if not primary_factors:
        return resolve_message(
            "explanation.headline.no_high_confidence",
            {"verdict": _verdict_lower(assessment.verdict)},
            language="es",
        )

    trust_context_factors = tuple(
        factor for factor in primary_factors if factor.score_contribution == 0
    )
    if assessment.risk_level == "SAFE" and trust_context_factors:
        drivers = ", ".join(factor.title for factor in trust_context_factors[:2])
        return resolve_message(
            "explanation.headline.safe_with_trust_context",
            {
                "verdict": _verdict_lower(assessment.verdict),
                "drivers": drivers,
            },
            language="es",
        )

    drivers = ", ".join(factor.title for factor in primary_factors[:2])
    return resolve_message(
        "explanation.headline.driven_by",
        {
            "verdict": _verdict_lower(assessment.verdict),
            "drivers": drivers,
        },
        language="es",
    )


def _build_spanish_decision_basis(
    assessment: RiskAssessmentDTO,
    primary_factors: tuple[ExplanationFactorDTO, ...],
    localized_signals: tuple[AnalysisSignalDTO, ...],
) -> str:
    trust_context_factors = tuple(
        factor for factor in primary_factors if factor.score_contribution == 0
    )
    category_summary = ", ".join(
        f"{_localize_category(category)}={penalty:.2f}"
        for category, penalty in sorted(
            assessment.category_breakdown.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if penalty > 0
    )
    if not category_summary:
        category_summary = resolve_message("phrase.no_category_penalties_recorded", language="es")

    if trust_context_factors and category_summary == resolve_message(
        "phrase.no_category_penalties_recorded",
        language="es",
    ):
        return resolve_message(
            "explanation.decision_basis.with_trust_context",
            {
                "score": assessment.score,
                "risk_level": _risk_level_lower(assessment.risk_level),
                "category_summary": category_summary,
                "drivers": ", ".join(factor.title for factor in trust_context_factors[:2]),
            },
            language="es",
        )

    dominant_signal = _select_dominant_explanation_signal_dto(localized_signals)
    if dominant_signal is not None and assessment.risk_level != "SAFE":
        return resolve_message(
            "explanation.decision_basis.primary_reason",
            {
                "reason": resolve_message(
                    _DOMINANT_EXPLANATION_REASON_KEYS[dominant_signal.signal_type],
                    language="es",
                ),
                "score": assessment.score,
                "risk_level": _risk_level_lower(assessment.risk_level),
                "category_summary": category_summary,
            },
            language="es",
        )

    if not primary_factors:
        return resolve_message(
            "explanation.decision_basis.no_primary_factors",
            {
                "score": assessment.score,
                "risk_level": _risk_level_lower(assessment.risk_level),
                "category_summary": category_summary,
            },
            language="es",
        )

    return resolve_message(
        "explanation.decision_basis.main_categories",
        {
            "score": assessment.score,
            "risk_level": _risk_level_lower(assessment.risk_level),
            "category_summary": category_summary,
        },
        language="es",
    )


def _select_dominant_explanation_signal_dto(
    signals: tuple[AnalysisSignalDTO, ...],
) -> AnalysisSignalDTO | None:
    eligible = [
        signal
        for signal in signals
        if signal.detected
        and signal.severity in {SignalSeverity.HIGH.value, SignalSeverity.CRITICAL.value}
        and signal.confidence > 80
        and signal.category in _DOMINANT_EXPLANATION_CATEGORIES
        and signal.signal_type in _DOMINANT_EXPLANATION_REASON_KEYS
        and signal.score_contribution > 0
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda signal: signal.score_contribution)


def _localized_top_signal_titles(
    signals: tuple[AnalysisSignalDTO, ...],
    max_items: int = 3,
) -> tuple[str, ...]:
    risk_signals = sorted(
        [signal for signal in signals if signal.detected and signal.score_contribution > 0],
        key=lambda signal: signal.score_contribution,
        reverse=True,
    )
    if risk_signals:
        return tuple(signal.title for signal in risk_signals[:max_items])

    informational = [signal for signal in signals if signal.detected]
    return tuple(signal.title for signal in informational[:max_items])


def _localize_title(value: str) -> str:
    return _TITLE_ES.get(value, value)


def _localize_description(value: str) -> str:
    return _DESCRIPTION_ES.get(value, value)


def _localize_warning(value: str) -> str:
    return _WARNING_ES.get(value, value)


def _localize_evidence(value: str) -> str:
    if value in _EVIDENCE_EXACT_ES:
        return _EVIDENCE_EXACT_ES[value]

    for pattern, template in _EVIDENCE_REGEX_ES:
        match = pattern.match(value)
        if match:
            return template.format(*match.groups())
    return value


def _localize_category(value: str) -> str:
    return _CATEGORY_ES.get(value, value)


def _verdict_lower(value: str) -> str:
    return _VERDICT_LOWER_ES.get(value, value.lower())


def _risk_level_lower(value: str) -> str:
    return _RISK_LEVEL_LOWER_ES.get(value, value.lower())
