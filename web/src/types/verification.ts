export type RiskLevel = "SAFE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type VerificationStatus = "PENDING" | "ANALYZING" | "COMPLETED" | "FAILED";

export type SignalSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type SignalStatus = "Observed" | "Correlated" | "Escalated" | "Pending review";

export interface VerificationSignal {
  id: string;
  title: string;
  description: string;
  reason: string;
  category: string;
  severity: SignalSeverity;
  confidence: number;
  source: string;
  scoreContribution: number;
  status: SignalStatus;
  evidence: string[];
}

export interface EvidenceSummary {
  observed: string[];
  sources: string[];
  supportingContext: string[];
  unresolved: string[];
}

export interface ExecutiveSummary {
  posture: string;
  operationalImpact: string;
}

export interface InconclusiveItem {
  id: string;
  title: string;
  detail: string;
  nextEvidence: string;
}

export interface RecommendedAction {
  title: string;
  detail: string;
  priority: string;
  owner: string;
}

export interface VerificationSummary {
  id: string;
  subject: string;
  normalizedInput: string;
  score: number;
  riskLevel: RiskLevel;
  verdict: string;
  status: VerificationStatus;
  createdAt: string;
  analystNote: string;
  summary: string;
  signals: VerificationSignal[];
  evidenceSummary: EvidenceSummary;
  executiveSummary: ExecutiveSummary;
  inconclusive: InconclusiveItem[];
  recommendation: RecommendedAction;
  decisionTrace: DecisionTraceStep[];
}

export interface ActivityItem {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
  actor: string;
  type: "verification_started" | "signal_detected" | "case_created" | "analyst_comment";
}

export interface DecisionTraceStep {
  id: string;
  label: string;
  detail: string;
  outcome: string;
  timestamp?: string;
}

export interface DashboardMetrics {
  pendingReviews: number;
  activeCases: number;
  highRiskQueue: number;
  flaggedSignals: number;
  lastVerificationAt: string;
  apiStatus: "Operational" | "Degraded" | "Unavailable";
  environmentLabel: string;
  confidencePosture: string;
  unresolvedEvidenceCount: number;
}

export interface HealthCheckResult {
  status: "ok" | "error";
  checkedAt: string;
  detail: string;
}
