export type RiskLevel = "SAFE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type UserPlan = "FREE" | "PRO";
export type QuotaPlan = UserPlan | "ANONYMOUS";
export type QuotaSubjectType = "ANONYMOUS" | "USER";

export type VerificationStatus = "pending" | "completed" | "failed";

export type SignalSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface VerificationSignal {
  id: string;
  signalType: string;
  detected: boolean;
  title: string;
  description: string;
  category: string;
  severity: SignalSeverity;
  confidence: number;
  source: string;
  baseWeight: number;
  scoreContribution: number;
  evidence: string[];
  tags: string[];
  createdAt: string;
}

export interface VerificationAnalysisTraceStep {
  stage: string;
  source: string;
  status: string;
  signalCount: number;
  signalTitles: string[];
  warnings: string[];
}

export interface VerificationExplanationFactor {
  signalType: string;
  title: string;
  source: string;
  severity: SignalSeverity;
  scoreContribution: number;
  evidence: string[];
}

export interface VerificationExplanation {
  headline: string;
  decisionBasis: string;
  primaryFactors: VerificationExplanationFactor[];
  analysisTrace: VerificationAnalysisTraceStep[];
  coverageWarnings: string[];
}

export interface VerificationTrace {
  layersExecuted: string[];
  signalsBySource: Record<string, VerificationSignal[]>;
  totalSignals: number;
}

export interface VerificationSignalContribution {
  signalType: string;
  baseWeight: number;
  confidence: number;
  impact: number;
}

export interface VerificationCompoundRuleDelta {
  ruleName: string;
  delta: number;
}

export interface VerificationScoreBreakdown {
  baseScore: number;
  signalContributions: VerificationSignalContribution[];
  compoundRulesApplied: VerificationCompoundRuleDelta[];
  finalScore: number;
}

export interface VerificationRiskAssessment {
  score: number;
  riskLevel: RiskLevel;
  verdict: string;
  summary: string;
  topSignals: string[];
  categoryBreakdown: Record<string, number>;
  terminalOverrideApplied: boolean;
  terminalReason: string | null;
  calculationVersion: string;
  analysisWarnings?: string[];
  analysisTrace?: VerificationAnalysisTraceStep[];
  explanation?: VerificationExplanation;
  calculatedAt: string;
}

export interface VerificationSummary {
  id: string;
  isOwned: boolean;
  targetType: string;
  originalInput: string;
  normalizedInput: string;
  status: VerificationStatus;
  riskAssessment: VerificationRiskAssessment;
  signals: VerificationSignal[];
  trace?: VerificationTrace;
  scoreBreakdown?: VerificationScoreBreakdown;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  calculationVersion: string;
  screenshotUrl?: string | null;
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
  terminal_override_applied: boolean;
  terminal_reason: string | null;
  calculation_version: string;
  analysis_warnings?: string[] | null;
  analysis_trace?: ApiAnalysisTraceStep[] | null;
  explanation?: ApiRiskExplanation | null;
  calculated_at: string;
}

export interface ApiAnalysisTrace {
  layers_executed: string[];
  signals_by_source: Record<string, ApiAnalysisSignal[]>;
  total_signals: number;
}

export interface ApiSignalContribution {
  signal_type: string;
  base_weight: number;
  confidence: number;
  impact: number;
}

export interface ApiCompoundRuleDelta {
  rule_name: string;
  delta: number;
}

export interface ApiScoreBreakdown {
  base_score: number;
  signal_contributions: ApiSignalContribution[];
  compound_rules_applied: ApiCompoundRuleDelta[];
  final_score: number;
}

export interface ApiAnalysisTraceStep {
  stage: string;
  source: string;
  status: string;
  signal_count: number;
  signal_titles: string[];
  warnings: string[];
}

export interface ApiExplanationFactor {
  signal_type: string;
  title: string;
  source: string;
  severity: SignalSeverity;
  score_contribution: number;
  evidence: string[];
}

export interface ApiRiskExplanation {
  headline: string;
  decision_basis: string;
  primary_factors: ApiExplanationFactor[];
  analysis_trace: ApiAnalysisTraceStep[];
  coverage_warnings: string[];
}

export interface ApiVerification {
  id: string;
  is_owned: boolean;
  target_type: string;
  original_input: string;
  normalized_input: string;
  status: VerificationStatus;
  signals: ApiAnalysisSignal[];
  risk_assessment: ApiRiskAssessment;
  trace?: ApiAnalysisTrace | null;
  score_breakdown?: ApiScoreBreakdown | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  calculation_version: string;
  screenshot_url?: string | null;
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
