export type RiskLevel = "SAFE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type UserPlan = "FREE" | "PRO";
export type QuotaPlan = UserPlan | "ANONYMOUS";
export type QuotaSubjectType = "ANONYMOUS" | "USER";

export type VerificationStatus = "PENDING" | "ANALYZING" | "COMPLETED" | "FAILED";

export type SignalSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type SignalStatus =
  | "Observed"
  | "Correlated"
  | "Escalated"
  | "Pending review"
  | "Observada"
  | "Correlacionada"
  | "Escalada"
  | "Pendiente de revisión";

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
  isOwned: boolean;
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

export interface DecisionTraceStep {
  id: string;
  label: string;
  detail: string;
  outcome: string;
  timestamp?: string;
}

export interface HealthCheckResult {
  status: "ok" | "error";
  checkedAt: string;
  detail: string;
}

export interface ApiAnalysisSignal {
  id: string;
  signal_type: string;
  category: string;
  severity: SignalSeverity;
  confidence: number;
  detected: boolean;
  title: string;
  description: string;
  evidence: string[];
  source: string;
  base_weight: number;
  score_contribution: number;
  tags: string[];
  created_at: string;
}

export interface ApiRiskAssessment {
  score: number;
  risk_level: RiskLevel;
  verdict: string;
  summary: string;
  top_signals: string[];
  category_breakdown: Record<string, number>;
  terminal_override: boolean;
  terminal_reason: string | null;
  calculation_version: string;
  calculated_at: string;
}

export interface ApiVerification {
  id: string;
  is_owned: boolean;
  target_type: string;
  original_input: string;
  normalized_input: string;
  status: VerificationStatus;
  signals: ApiAnalysisSignal[];
  risk_assessment: ApiRiskAssessment | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  calculation_version: string;
}

export interface CreateVerificationInput {
  url: string;
}

export interface EmailLoginInput {
  email: string;
  password: string;
}

export interface EmailRegistrationInput extends EmailLoginInput {
  display_name: string;
}

export interface ApiUser {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  plan: UserPlan;
  created_at: string;
}

export interface ApiAuthSession {
  access_token: string;
  token_type: string;
  user: ApiUser;
}

export interface ApiQuotaStatus {
  subject_type: QuotaSubjectType;
  is_authenticated: boolean;
  plan: QuotaPlan;
  daily_limit: number;
  used_today: number;
  remaining_today: number;
  reset_at_utc: string;
  reset_in_seconds: number;
  blocked: boolean;
}
