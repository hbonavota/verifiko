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

function titleCase(value: string): string {
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function signalStatusForSeverity(severity: ApiAnalysisSignal["severity"]): SignalStatus {
  if (severity === "CRITICAL" || severity === "HIGH") {
    return "Escalated";
  }
  if (severity === "MEDIUM") {
    return "Correlated";
  }
  return "Observed";
}

function signalReason(signal: ApiAnalysisSignal): string {
  const evidenceLead = signal.evidence[0];
  if (evidenceLead) {
    return `${signal.description} ${evidenceLead}`;
  }
  return signal.description;
}

function mapSignal(signal: ApiAnalysisSignal): VerificationSignal {
  return {
    id: signal.id,
    title: signal.title,
    description: signal.description,
    reason: signalReason(signal),
    category: titleCase(signal.category),
    severity: signal.severity,
    confidence: signal.confidence,
    source: signal.source,
    scoreContribution: Math.round(signal.score_contribution * 10) / 10,
    status: signalStatusForSeverity(signal.severity),
    evidence: signal.evidence,
  };
}

function buildEvidenceSummary(verification: ApiVerification, signals: VerificationSignal[]): EvidenceSummary {
  const observed = signals.map((signal) => signal.description);
  const supportingContext = [
    `Input normalized to ${verification.normalized_input}.`,
    `Calculated with version ${verification.calculation_version}.`,
  ];

  if (verification.risk_assessment?.terminal_reason) {
    supportingContext.push(`Terminal reason: ${verification.risk_assessment.terminal_reason}.`);
  }

  return {
    observed,
    sources: [...new Set(signals.map((signal) => signal.source))],
    supportingContext,
    unresolved:
      signals.length === 0
        ? ["No suspicious indicators were retained from the current verification run."]
        : [
            "This assessment combines URL structure analysis with additional checks such as domain age, page credential patterns, and transport security validation when available.",
            "The current record still lacks deeper infrastructure history such as passive DNS, hosting lineage, and reputation feeds.",
          ],
  };
}

function buildInconclusiveItems(verification: ApiVerification): InconclusiveItem[] {
  if (verification.signals.length === 0) {
    return [
      {
        id: `${verification.id}-inc-1`,
        title: "No suspicious signals were retained",
        detail: "The current verification did not retain a suspicious signal from the available checks.",
        nextEvidence: "Add broader infrastructure or content context if you need a deeper review.",
      },
    ];
  }

  return [
    {
      id: `${verification.id}-inc-1`,
      title: "Infrastructure context is not attached",
      detail: "This vertical slice does not yet include DNS, hosting, certificate, or reputation enrichment.",
      nextEvidence: "Attach passive DNS, registrar, or hosting history before making a final containment decision.",
    },
  ];
}

function buildRecommendation(verification: ApiVerification): RecommendedAction {
  const riskLevel = verification.risk_assessment?.risk_level ?? "LOW";

  if (riskLevel === "CRITICAL" || riskLevel === "HIGH") {
    return {
      title: "Escalate for analyst review",
      detail: "The URL triggered multiple high-signal indicators and should move into active review.",
      priority: "High priority",
      owner: "Verification response queue",
    };
  }

  if (riskLevel === "MEDIUM") {
    return {
      title: "Queue for deeper validation",
      detail: "The result is suspicious enough to justify follow-up, but it still lacks infrastructure confirmation.",
      priority: "Priority review",
      owner: "Threat review queue",
    };
  }

  return {
    title: "Retain for monitoring",
    detail: "No strong risk signal was produced from the URL alone, so monitoring is more appropriate than escalation.",
    priority: "Routine review",
    owner: "Verification triage",
  };
}

function buildDecisionTrace(verification: ApiVerification, signals: VerificationSignal[]): DecisionTraceStep[] {
  const steps: DecisionTraceStep[] = [
    {
      id: `${verification.id}-trace-1`,
      label: "Normalized input",
      detail: `Input was normalized to ${verification.normalized_input}.`,
      outcome: "Stable verification object created",
      timestamp: verification.created_at,
    },
    {
      id: `${verification.id}-trace-2`,
      label: "Derived URL signals",
      detail:
        signals.length > 0
          ? `${signals.length} deterministic URL signal(s) were retained from the host, path, and query structure.`
          : "No deterministic URL signals crossed the retention threshold.",
      outcome:
        signals.length > 0 ? `${signals.length} signal(s) attached to the verification record` : "Verification kept with zero retained signals",
      timestamp: verification.updated_at,
    },
  ];

  if (verification.risk_assessment) {
    steps.push({
      id: `${verification.id}-trace-3`,
      label: "Calculated score",
      detail: verification.risk_assessment.summary,
      outcome: `Risk score set to ${verification.risk_assessment.score} with verdict ${verification.risk_assessment.verdict}`,
      timestamp: verification.risk_assessment.calculated_at,
    });
  }

  return steps;
}

export function adaptApiVerification(verification: ApiVerification): VerificationSummary {
  const signals = verification.signals
    .map(mapSignal)
    .sort((left, right) => right.scoreContribution - left.scoreContribution);
  const evidenceSummary = buildEvidenceSummary(verification, signals);
  const recommendation = buildRecommendation(verification);

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
        ? "The current result is based on the implemented verification checks, including URL analysis and available request-time enrichments."
        : "No suspicious signal was retained from the checks executed in this local slice.",
    summary:
      verification.risk_assessment?.summary ??
      "No suspicious signal was generated from the submitted URL.",
    signals,
    evidenceSummary,
    executiveSummary: {
      posture:
        verification.signals.length > 0
          ? `Current posture is ${verification.risk_assessment?.risk_level ?? "LOW"} risk based on the signals retained by the current verification checks.`
          : "Current posture is low-risk because the implemented checks did not retain suspicious indicators.",
      operationalImpact:
        verification.signals.length > 0
          ? "The verification can be reviewed immediately, but it still benefits from broader infrastructure context for higher-confidence decisions."
          : "This result should not be treated as a clean bill of health without broader content or infrastructure context.",
    },
    inconclusive: buildInconclusiveItems(verification),
    recommendation,
    decisionTrace: buildDecisionTrace(verification, signals),
  };
}
