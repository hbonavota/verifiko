import type {
  ApiAnalysisSignal,
  ApiAnalysisTrace,
  ApiAnalysisTraceStep,
  ApiCompoundRuleDelta,
  ApiExplanationFactor,
  ApiRiskAssessment,
  ApiRiskExplanation,
  ApiScoreBreakdown,
  ApiSignalContribution,
  ApiVerification,
  VerificationCompoundRuleDelta,
  VerificationAnalysisTraceStep,
  VerificationExplanation,
  VerificationExplanationFactor,
  VerificationRiskAssessment,
  VerificationScoreBreakdown,
  VerificationSignalContribution,
  VerificationSignal,
  VerificationSummary,
  VerificationTrace,
} from "../types/verification";
import type { Language } from "./i18n";

function titleCase(value: string): string {
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

// Decision-trace stage status comes from the backend as a stable key
// (signals_detected / clean / degraded). Localize the known ones; fall back to
// a readable title-case for anything new.
function localizeTraceStatus(status: string, language: Language): string {
  const key = status.trim().toLowerCase().replace(/[\s-]+/g, "_");
  const labels: Record<string, { en: string; es: string }> = {
    signals_detected: { en: "Signals detected", es: "Señales detectadas" },
    clean: { en: "Clean", es: "Sin señales" },
    degraded: { en: "Partial coverage", es: "Cobertura parcial" },
  };
  return labels[key]?.[language] ?? titleCase(status);
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
    "content-analyzer": language === "es" ? "Análisis de contenido" : "Content analysis",
    "network-check": language === "es" ? "Comprobación de red" : "Network check",
    "nlp-analyzer": language === "es" ? "Análisis lingüístico" : "Language analysis",
    "redirect-resolver": language === "es" ? "Resolución de redirecciones" : "Redirect resolution",
    "url-rule-analyzer": language === "es" ? "Análisis de URL" : "URL analysis",
    "url-normalizer": language === "es" ? "Normalización de URL" : "URL normalization",
    "redirect-chain-analyzer": language === "es" ? "Análisis de redirecciones" : "Redirect analysis",
    "resolved-destination-url-analyzer":
      language === "es" ? "Análisis de URL del destino final" : "Final-destination URL analysis",
    "resolved-destination-html-analyzer":
      language === "es" ? "Análisis HTML del destino final" : "Final-destination HTML analysis",
    "resolved-destination-analysis":
      language === "es" ? "Análisis del destino final" : "Final-destination analysis",
    "html-credential-analyzer": language === "es" ? "Análisis HTML" : "HTML analysis",
    "threat-feed": language === "es" ? "Fuente de amenazas" : "Threat feed",
    "transport-security-analyzer":
      language === "es" ? "Análisis de transporte seguro" : "Transport security analysis",
    "domain-recency-analyzer":
      language === "es" ? "Análisis de antigüedad del dominio" : "Domain age analysis",
    "infrastructure-intelligence-analyzer":
      language === "es" ? "Análisis de infraestructura" : "Infrastructure analysis",
    "reputation-analyzer": language === "es" ? "Análisis de reputación" : "Reputation analysis",
    "trusted-signal-input": language === "es" ? "Señal de confianza aportada" : "Trusted signal input",
  } as const;

  return labels[normalized as keyof typeof labels] ?? titleCase(source.replace(/-/g, " "));
}

function mapSignal(signal: ApiAnalysisSignal, language: Language): VerificationSignal {
  return {
    id: signal.id,
    signalType: signal.signal_type,
    detected: signal.detected,
    title: signal.title,
    description: signal.description,
    category: formatSignalCategory(signal.category, language),
    severity: signal.severity,
    confidence: signal.confidence,
    source: formatSignalSource(signal.source, language),
    baseWeight: signal.base_weight,
    scoreContribution: Math.round(signal.score_contribution * 10) / 10,
    evidence: signal.evidence,
    tags: signal.tags,
    createdAt: signal.created_at,
  };
}

function mapAnalysisTraceStep(step: ApiAnalysisTraceStep, language: Language): VerificationAnalysisTraceStep {
  return {
    stage: titleCase(step.stage),
    source: formatSignalSource(step.source, language),
    status: localizeTraceStatus(step.status, language),
    signalCount: step.signal_count,
    signalTitles: step.signal_titles,
    warnings: step.warnings,
  };
}

function mapTrace(trace: ApiAnalysisTrace, language: Language): VerificationTrace {
  return {
    layersExecuted: trace.layers_executed,
    signalsBySource: Object.fromEntries(
      Object.entries(trace.signals_by_source).map(([source, signals]) => [
        formatSignalSource(source, language),
        signals.map((signal) => mapSignal(signal, language)),
      ]),
    ),
    totalSignals: trace.total_signals,
  };
}

function mapSignalContribution(
  contribution: ApiSignalContribution,
): VerificationSignalContribution {
  return {
    signalType: contribution.signal_type,
    baseWeight: contribution.base_weight,
    confidence: contribution.confidence,
    impact: contribution.impact,
  };
}

function mapCompoundRuleDelta(delta: ApiCompoundRuleDelta): VerificationCompoundRuleDelta {
  return {
    ruleName: delta.rule_name,
    delta: delta.delta,
  };
}

function mapScoreBreakdown(breakdown: ApiScoreBreakdown): VerificationScoreBreakdown {
  return {
    baseScore: breakdown.base_score,
    signalContributions: breakdown.signal_contributions.map(mapSignalContribution),
    compoundRulesApplied: breakdown.compound_rules_applied.map(mapCompoundRuleDelta),
    finalScore: breakdown.final_score,
  };
}

function mapExplanationFactor(
  factor: ApiExplanationFactor,
  language: Language,
): VerificationExplanationFactor {
  return {
    signalType: factor.signal_type,
    title: factor.title,
    source: formatSignalSource(factor.source, language),
    severity: factor.severity,
    scoreContribution: factor.score_contribution,
    evidence: factor.evidence,
  };
}

function mapExplanation(
  explanation: ApiRiskExplanation,
  language: Language,
): VerificationExplanation {
  return {
    headline: explanation.headline,
    decisionBasis: explanation.decision_basis,
    primaryFactors: explanation.primary_factors.map((factor) => mapExplanationFactor(factor, language)),
    analysisTrace: explanation.analysis_trace.map((step) => mapAnalysisTraceStep(step, language)),
    coverageWarnings: explanation.coverage_warnings,
  };
}

function mapRiskAssessment(
  assessment: ApiRiskAssessment,
  language: Language,
): VerificationRiskAssessment {
  return {
    score: assessment.score,
    riskLevel: assessment.risk_level,
    verdict: assessment.verdict,
    summary: assessment.summary,
    topSignals: assessment.top_signals,
    categoryBreakdown: assessment.category_breakdown,
    terminalOverrideApplied: assessment.terminal_override_applied,
    terminalReason: assessment.terminal_reason,
    calculationVersion: assessment.calculation_version,
    analysisWarnings: assessment.analysis_warnings ?? undefined,
    analysisTrace: assessment.analysis_trace?.map((step) =>
      mapAnalysisTraceStep(step, language),
    ),
    explanation: assessment.explanation ? mapExplanation(assessment.explanation, language) : undefined,
    calculatedAt: assessment.calculated_at,
  };
}

export function adaptApiVerification(
  verification: ApiVerification,
  language: Language = "en",
): VerificationSummary {
  return {
    id: verification.id,
    isOwned: verification.is_owned,
    targetType: verification.target_type,
    originalInput: verification.original_input,
    normalizedInput: verification.normalized_input,
    status: verification.status,
    signals: verification.signals.map((signal) => mapSignal(signal, language)),
    riskAssessment: mapRiskAssessment(verification.risk_assessment, language),
    trace: verification.trace ? mapTrace(verification.trace, language) : undefined,
    scoreBreakdown: verification.score_breakdown
      ? mapScoreBreakdown(verification.score_breakdown)
      : undefined,
    createdAt: verification.created_at,
    updatedAt: verification.updated_at,
    completedAt: verification.completed_at,
    calculationVersion: verification.calculation_version,
    screenshotUrl: verification.screenshot_url ?? null,
  };
}
