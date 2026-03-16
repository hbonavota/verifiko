import type {
  ActivityItem,
  DashboardMetrics,
  DecisionTraceStep,
  VerificationSummary,
} from "../types/verification";
import { mockVerifications } from "./mockVerifications";

export const currentVerification: VerificationSummary =
  mockVerifications.find((verification) => verification.id === "vfk-2421") ?? mockVerifications[0];

export const dashboardMetrics: DashboardMetrics = {
  pendingReviews: 12,
  activeCases: 4,
  highRiskQueue: 3,
  flaggedSignals: 19,
  lastVerificationAt: "2026-03-15T10:48:00Z",
  apiStatus: "Operational",
  environmentLabel: "Local demo workspace",
  confidencePosture: "Medium confidence pending infrastructure context",
  unresolvedEvidenceCount: 2,
};

export const activityFeed: ActivityItem[] = [
  {
    id: "act-1",
    title: "Verification started",
    detail: "New review initiated for payroll-gateway.net from analyst intake panel.",
    timestamp: "2026-03-15T10:12:00Z",
    actor: "Shift queue",
    type: "verification_started",
  },
  {
    id: "act-2",
    title: "Signal detected",
    detail: "Misleading subdomain signal correlated with content-level credential lure wording.",
    timestamp: "2026-03-15T10:16:00Z",
    actor: "Scoring engine",
    type: "signal_detected",
  },
  {
    id: "act-3",
    title: "Case created",
    detail: "Medium-risk verification promoted to analyst case for disposition review.",
    timestamp: "2026-03-15T10:19:00Z",
    actor: "Workflow service",
    type: "case_created",
  },
  {
    id: "act-4",
    title: "Analyst comment",
    detail: "Passive DNS and hosting context requested before final action recommendation.",
    timestamp: "2026-03-15T10:27:00Z",
    actor: "A. Navarro",
    type: "analyst_comment",
  },
];

export const decisionTrace: DecisionTraceStep[] = [
  {
    id: "trace-1",
    label: "Normalized input",
    detail: "Input normalized to https://payroll-gateway.net/ with canonical host and path retained.",
    outcome: "Stable verification object created",
  },
  {
    id: "trace-2",
    label: "Collected signals",
    detail: "Redirect behavior, domain structure cues, and credential-lure content signals were observed.",
    outcome: "3 active signals retained for scoring",
  },
  {
    id: "trace-3",
    label: "Applied penalties",
    detail: "Domain structure and content behavior contributed most of the score movement, with navigation behavior adding secondary weight.",
    outcome: "Category penalties totaled 50",
  },
  {
    id: "trace-4",
    label: "Calculated score",
    detail: "Final score derived from category penalties without a terminal override condition.",
    outcome: "Risk score set to 58 · verdict Suspicious",
  },
  {
    id: "trace-5",
    label: "Generated explanation summary",
    detail: "Most influential signals and analyst next-step framing were attached to the verification record.",
    outcome: "Readable explanation available for review",
  },
];

export const flagReasons = [
  "The hostname structure implies a trusted payroll context without matching ownership evidence.",
  "Observed content language pushes account validation and credential re-entry with elevated urgency.",
  "Redirect behavior increases suspicion because the apparent entry point does not match the final rendered experience.",
] as const;
