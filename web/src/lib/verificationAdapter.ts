import type {
  ApiAnalysisSignal,
  ApiVerification,
  DecisionTraceStep,
  EvidenceSummary,
  InconclusiveItem,
  RecommendedAction,
  SignalStatus,
  VerificationSignal,
  VerificationSummary,
} from "../types/verification";
import type { Language } from "./i18n";
import { formatRiskLevel, formatVerdict } from "./formatVerdict";

function titleCase(value: string): string {
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function signalStatusForSeverity(severity: ApiAnalysisSignal["severity"], language: Language): SignalStatus {
  if (severity === "CRITICAL" || severity === "HIGH") {
    return language === "es" ? "Escalada" : "Escalated";
  }
  if (severity === "MEDIUM") {
    return language === "es" ? "Correlacionada" : "Correlated";
  }
  return language === "es" ? "Observada" : "Observed";
}

function formatSignalCategory(category: string, language: Language): string {
  const normalized = category.trim().toUpperCase();
  const labels = {
    DOMAIN_REPUTATION: language === "es" ? "Reputación del dominio" : "Domain reputation",
    DOMAIN_STRUCTURE: language === "es" ? "Estructura del dominio" : "Domain structure",
    NETWORK_TRANSPORT: language === "es" ? "Transporte de red" : "Network transport",
    NAVIGATION_BEHAVIOR: language === "es" ? "Comportamiento de navegación" : "Navigation behavior",
    CONTENT_BEHAVIOR: language === "es" ? "Comportamiento del contenido" : "Content behavior",
  } as const;

  return labels[normalized as keyof typeof labels] ?? titleCase(category);
}

function formatSignalSource(source: string, language: Language): string {
  const normalized = source.trim().toLowerCase();
  const labels = {
    "url-rule-analyzer": language === "es" ? "Análisis de URL" : "URL analysis",
    "redirect-chain-analyzer": language === "es" ? "Análisis de redirecciones" : "Redirect analysis",
    "resolved-destination-url-analyzer":
      language === "es" ? "Análisis de URL del destino final" : "Final-destination URL analysis",
    "resolved-destination-html-analyzer":
      language === "es" ? "Análisis HTML del destino final" : "Final-destination HTML analysis",
    "html-credential-analyzer": language === "es" ? "Análisis HTML" : "HTML analysis",
    "transport-security-analyzer":
      language === "es" ? "Análisis de transporte seguro" : "Transport security analysis",
    "domain-recency-analyzer":
      language === "es" ? "Análisis de antigüedad del dominio" : "Domain age analysis",
    "infrastructure-intelligence-analyzer":
      language === "es" ? "Análisis de infraestructura" : "Infrastructure analysis",
    "reputation-analyzer": language === "es" ? "Análisis de reputación" : "Reputation analysis",
  } as const;

  return labels[normalized as keyof typeof labels] ?? titleCase(source.replace(/-/g, " "));
}

function signalReason(signal: ApiAnalysisSignal): string {
  const evidenceLead = signal.evidence[0];
  if (evidenceLead) {
    return `${signal.description} ${evidenceLead}`;
  }
  return signal.description;
}

function mapSignal(signal: ApiAnalysisSignal, language: Language): VerificationSignal {
  return {
    id: signal.id,
    title: signal.title,
    description: signal.description,
    reason: signalReason(signal),
    category: formatSignalCategory(signal.category, language),
    severity: signal.severity,
    confidence: signal.confidence,
    source: formatSignalSource(signal.source, language),
    scoreContribution: Math.round(signal.score_contribution * 10) / 10,
    status: signalStatusForSeverity(signal.severity, language),
    evidence: signal.evidence,
  };
}

function buildEvidenceSummary(
  verification: ApiVerification,
  signals: VerificationSignal[],
  language: Language,
): EvidenceSummary {
  const observed = signals.map((signal) => signal.description);
  const supportingContext = [
    language === "es"
      ? `El enlace enviado se normalizó a ${verification.normalized_input}.`
      : `Submitted link normalized to ${verification.normalized_input}.`,
    language === "es"
      ? `Resultado generado con la versión ${verification.calculation_version} del motor de verificación.`
      : `Result generated with verification engine version ${verification.calculation_version}.`,
  ];

  if (verification.risk_assessment?.terminal_reason) {
    supportingContext.push(
      language === "es"
        ? `Motivo de la decisión final: ${verification.risk_assessment.terminal_reason}.`
        : `Final decision reason: ${verification.risk_assessment.terminal_reason}.`,
    );
  }

  return {
    observed,
    sources: [...new Set(signals.map((signal) => signal.source))],
    supportingContext,
    unresolved:
      signals.length === 0
        ? [
            language === "es"
              ? "No se retuvo ninguna señal de alerta fuerte en esta verificación."
              : "No strong warning signal was retained in this verification.",
          ]
        : [
            language === "es"
              ? "Este resultado combina las comprobaciones completadas durante la verificación, incluido el destino, el transporte y la revisión de la página cuando estuvieron disponibles."
              : "This result combines the checks completed during verification, including destination, transport, and page review when available.",
            language === "es"
              ? "El historial más amplio de la infraestructura no está incluido en esta vista."
              : "Broader infrastructure history is not included in this view.",
          ],
  };
}

function buildInconclusiveItems(verification: ApiVerification, language: Language): InconclusiveItem[] {
  if (verification.signals.length === 0) {
    return [
      {
        id: `${verification.id}-inc-1`,
        title:
          language === "es" ? "No se retuvo una señal de alerta fuerte" : "No strong warning signal was retained",
        detail:
          language === "es"
            ? "Esta verificación no retuvo una señal de alerta fuerte de las comprobaciones que se completaron."
            : "This verification did not retain a strong warning signal from the checks that completed.",
        nextEvidence:
          language === "es"
            ? "Usa más contexto antes de tratar el enlace como seguro."
            : "Use more context before treating the link as safe.",
      },
    ];
  }

  return [
    {
      id: `${verification.id}-inc-1`,
      title: language === "es" ? "Más contexto puede cambiar el resultado" : "More context may change the result",
      detail:
        language === "es"
          ? "Este resultado refleja las comprobaciones completadas durante la verificación, no el historial completo del objetivo."
          : "This result reflects the checks completed during verification, not the full history of the target.",
      nextEvidence:
        language === "es"
          ? "Revisa más contexto de dominio, alojamiento o reputación antes de tomar una decisión final."
          : "Review additional domain, hosting, or reputation context before making a final decision.",
    },
  ];
}

function buildRecommendation(verification: ApiVerification, language: Language): RecommendedAction {
  const riskLevel = verification.risk_assessment?.risk_level ?? "LOW";

  if (riskLevel === "CRITICAL" || riskLevel === "HIGH") {
    return {
      title: language === "es" ? "Escalar para revisión" : "Escalate for review",
      detail:
        language === "es"
          ? "Este enlace activó varias señales de alerta fuertes y debe revisarse ahora."
          : "This link triggered multiple strong warning signals and should be reviewed now.",
      priority: language === "es" ? "Alta prioridad" : "High priority",
      owner: language === "es" ? "Cola de respuesta de verificación" : "Verification response queue",
    };
  }

  if (riskLevel === "MEDIUM") {
    return {
      title: language === "es" ? "Revisar antes de confiar" : "Review before trusting",
      detail:
        language === "es"
          ? "Este resultado necesita seguimiento antes de tratar el enlace como seguro."
          : "This result needs follow-up before the link is treated as safe.",
      priority: language === "es" ? "Revisión prioritaria" : "Priority review",
      owner: language === "es" ? "Cola de revisión de amenazas" : "Threat review queue",
    };
  }

  return {
    title: language === "es" ? "Mantener en observación" : "Keep under watch",
    detail:
      language === "es"
        ? "No se retuvo una señal de alerta fuerte, pero esto no es una garantía de seguridad."
        : "No strong warning signal was retained, but this is not a guarantee of safety.",
    priority: language === "es" ? "Revisión rutinaria" : "Routine review",
    owner: language === "es" ? "Triaje de verificación" : "Verification triage",
  };
}

function buildDecisionTrace(
  verification: ApiVerification,
  signals: VerificationSignal[],
  language: Language,
): DecisionTraceStep[] {
  const steps: DecisionTraceStep[] = [
    {
      id: `${verification.id}-trace-1`,
      label: language === "es" ? "Entrada preparada" : "Input prepared",
      detail:
        language === "es"
          ? `El enlace enviado se normalizó a ${verification.normalized_input}.`
          : `Submitted link normalized to ${verification.normalized_input}.`,
      outcome: language === "es" ? "Verificación iniciada" : "Verification started",
      timestamp: verification.created_at,
    },
    {
      id: `${verification.id}-trace-2`,
      label: language === "es" ? "Señales revisadas" : "Signals reviewed",
      detail:
        signals.length > 0
          ? language === "es"
            ? `Se retuvieron ${signals.length} señal(es) de las comprobaciones de verificación.`
            : `${signals.length} signal(s) were retained from the verification checks.`
          : language === "es"
            ? "Ninguna señal superó el umbral de retención."
            : "No signal crossed the retention threshold.",
      outcome:
        signals.length > 0
          ? language === "es"
            ? `${signals.length} señal(es) retenidas`
            : `${signals.length} signal(s) retained`
          : language === "es"
            ? "Sin señales retenidas"
            : "No retained signals",
      timestamp: verification.updated_at,
    },
  ];

  if (verification.risk_assessment) {
    steps.push({
      id: `${verification.id}-trace-3`,
      label: language === "es" ? "Resultado calculado" : "Result calculated",
      detail: verification.risk_assessment.summary,
      outcome:
        language === "es"
          ? `Puntuación ${verification.risk_assessment.score} con veredicto ${formatVerdict(verification.risk_assessment.verdict, language)}`
          : `Score ${verification.risk_assessment.score} with verdict ${formatVerdict(verification.risk_assessment.verdict, language)}`,
      timestamp: verification.risk_assessment.calculated_at,
    });
  }

  return steps;
}

export function adaptApiVerification(verification: ApiVerification, language: Language = "en"): VerificationSummary {
  const signals = verification.signals
    .map((signal) => mapSignal(signal, language))
    .sort((left, right) => right.scoreContribution - left.scoreContribution);
  const evidenceSummary = buildEvidenceSummary(verification, signals, language);
  const recommendation = buildRecommendation(verification, language);

  return {
    id: verification.id,
    subject: verification.original_input,
    normalizedInput: verification.normalized_input,
    score: verification.risk_assessment?.score ?? 100,
    riskLevel: verification.risk_assessment?.risk_level ?? "SAFE",
    verdict: verification.risk_assessment?.verdict ?? "Trusted",
    status: verification.status,
    createdAt: verification.created_at,
    analystNote:
      verification.signals.length > 0
        ? language === "es"
          ? "Este resultado refleja las comprobaciones completadas para este enlace durante la verificación."
          : "This result reflects the checks completed for this link during verification."
        : language === "es"
          ? "No se retuvo una señal de alerta fuerte en esta verificación."
          : "No strong warning signal was retained in this verification.",
    summary:
      verification.risk_assessment?.summary ??
      (language === "es"
        ? "No se generó ninguna señal de alerta a partir del enlace enviado."
        : "No warning signal was generated from the submitted link."),
    signals,
    evidenceSummary,
    executiveSummary: {
      posture:
      verification.signals.length > 0
        ? language === "es"
            ? `Riesgo ${formatRiskLevel(verification.risk_assessment?.risk_level ?? "LOW", language)} basado en las señales retenidas en esta verificación.`
            : `${formatRiskLevel(verification.risk_assessment?.risk_level ?? "LOW", language)} risk based on the signals retained in this verification.`
          : language === "es"
            ? "No se retuvo una señal de alerta fuerte en esta verificación."
            : "No strong warning signal was retained in this verification.",
      operationalImpact:
        verification.signals.length > 0
          ? language === "es"
            ? "Revisa las señales retenidas antes de tomar una decisión final."
            : "Review the retained signals before making a final decision."
          : language === "es"
            ? "Trata este resultado con cautela si aún falta contexto más amplio."
            : "Treat this result with care if broader context is still missing.",
    },
    inconclusive: buildInconclusiveItems(verification, language),
    recommendation,
    decisionTrace: buildDecisionTrace(verification, signals, language),
  };
}
