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
    `Submitted link normalized to ${verification.normalized_input}.`,
    `Result generated with verification engine version ${verification.calculation_version}.`,
  ];

  if (verification.risk_assessment?.terminal_reason) {
    supportingContext.push(`Final decision reason: ${verification.risk_assessment.terminal_reason}.`);
  }

  return {
    observed,
    sources: [...new Set(signals.map((signal) => signal.source))],
    supportingContext,
    unresolved:
      signals.length === 0
        ? ["No strong warning signal was retained in this verification."]
        : [
            "This result combines the checks completed during verification, including destination, transport, and page review when available.",
            "Broader infrastructure history is not included in this view.",
          ],
  };
}

function buildInconclusiveItems(verification: ApiVerification): InconclusiveItem[] {
  if (verification.signals.length === 0) {
    return [
      {
        id: `${verification.id}-inc-1`,
        title: "No strong warning signal was retained",
        detail: "This verification did not retain a strong warning signal from the checks that completed.",
        nextEvidence: "Use more context before treating the link as safe.",
      },
    ];
  }

  return [
    {
      id: `${verification.id}-inc-1`,
      title: "More context may change the result",
      detail: "This result reflects the checks completed during verification, not the full history of the target.",
      nextEvidence: "Review additional domain, hosting, or reputation context before making a final decision.",
    },
  ];
}

function buildRecommendation(verification: ApiVerification): RecommendedAction {
  const riskLevel = verification.risk_assessment?.risk_level ?? "LOW";

  if (riskLevel === "CRITICAL" || riskLevel === "HIGH") {
    return {
      title: "Escalate for review",
      detail: "This link triggered multiple strong warning signals and should be reviewed now.",
      priority: "High priority",
      owner: "Verification response queue",
    };
  }

  if (riskLevel === "MEDIUM") {
    return {
      title: "Review before trusting",
      detail: "This result needs follow-up before the link is treated as safe.",
      priority: "Priority review",
      owner: "Threat review queue",
    };
  }

  return {
    title: "Keep under watch",
    detail: "No strong warning signal was retained, but this is not a guarantee of safety.",
    priority: "Routine review",
    owner: "Verification triage",
  };
}

function buildDecisionTrace(verification: ApiVerification, signals: VerificationSignal[]): DecisionTraceStep[] {
  const steps: DecisionTraceStep[] = [
    {
      id: `${verification.id}-trace-1`,
      label: "Input prepared",
      detail: `Submitted link normalized to ${verification.normalized_input}.`,
      outcome: "Verification started",
      timestamp: verification.created_at,
    },
    {
      id: `${verification.id}-trace-2`,
      label: "Signals reviewed",
      detail:
        signals.length > 0
          ? `${signals.length} signal(s) were retained from the verification checks.`
          : "No signal crossed the retention threshold.",
      outcome:
        signals.length > 0 ? `${signals.length} signal(s) retained` : "No retained signals",
      timestamp: verification.updated_at,
    },
  ];

  if (verification.risk_assessment) {
    steps.push({
      id: `${verification.id}-trace-3`,
      label: "Result calculated",
      detail: verification.risk_assessment.summary,
      outcome: `Score ${verification.risk_assessment.score} with verdict ${verification.risk_assessment.verdict}`,
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
        ? "This result reflects the checks completed for this link during verification."
        : "No strong warning signal was retained in this verification.",
    summary:
      verification.risk_assessment?.summary ??
      "No warning signal was generated from the submitted link.",
    signals,
    evidenceSummary,
    executiveSummary: {
      posture:
        verification.signals.length > 0
          ? `${verification.risk_assessment?.risk_level ?? "LOW"} risk based on the signals retained in this verification.`
          : "No strong warning signal was retained in this verification.",
      operationalImpact:
        verification.signals.length > 0
          ? "Review the retained signals before making a final decision."
          : "Treat this result with care if broader context is still missing.",
    },
    inconclusive: buildInconclusiveItems(verification),
    recommendation,
    decisionTrace: buildDecisionTrace(verification, signals),
  };
}
