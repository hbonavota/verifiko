import { applyAnalyticsConsent, readAnalyticsConsentChoice } from "./analyticsConsent";
import type { ApiVerification } from "../types/verification";

const DEGRADED_COVERAGE_PATTERN =
  /analysis coverage degraded|cobertura de análisis degradada|cobertura de analisis degradada/i;

type AnalyticsParams = Record<string, string | number | boolean>;
type AnalyticsPlan = "ANONYMOUS" | "FREE" | "PRO";
type PageEventName = "verify_page_view" | "review_page_view" | "status_page_view";

const trackedNamedPageViewKeys = new Set<string>();

interface AnalyticsContextParams {
  language: string;
  sourcePath: string;
  isAuthenticated: boolean;
  plan: AnalyticsPlan;
}

interface PageViewParams {
  pagePath: string;
  pageTitle: string;
  language: string;
}

interface NamedPageViewParams extends AnalyticsContextParams {
  eventName: PageEventName;
}

interface AnalysisInputStartedParams extends AnalyticsContextParams {
  inputMethod: "manual" | "paste";
}

interface AnalysisStartedParams extends AnalyticsContextParams {
  inputType: "manual" | "paste";
  hasProtocol: boolean;
}

interface AnalysisCompletedParams extends AnalyticsContextParams {
  riskLevel: string;
  verdict: string;
  signalCount: number;
  warningCount: number;
  hasFetchDegradation: boolean;
}

interface AnalysisFailedParams extends AnalyticsContextParams {
  errorType: string;
}

interface QuotaPromptShownParams extends AnalyticsContextParams {
  promptType: "blocked_anonymous" | "blocked_free" | "blocked_pro" | "support_note_anonymous";
}

interface QuotaBlockedParams extends AnalyticsContextParams {
  retryAfterSeconds: number | null;
}

interface AuthEntryClickedParams extends AnalyticsContextParams {
  entryPoint: string;
}

interface ResultActionClickedParams extends AnalyticsContextParams {
  action: "view_result" | "review_signals" | "verify_another_link";
  resultState: "latest_result" | "signed_in_empty";
}

interface UpgradeIntentClickedParams extends AnalyticsContextParams {
  source: string;
}

function buildAnalyticsContext({
  language,
  sourcePath,
  isAuthenticated,
  plan,
}: AnalyticsContextParams): AnalyticsParams {
  return {
    language,
    source_path: sourcePath,
    is_authenticated: isAuthenticated,
    plan,
  };
}

function ensureAnalyticsReady(): boolean {
  if (readAnalyticsConsentChoice() !== "granted") {
    return false;
  }

  applyAnalyticsConsent("granted");
  return Boolean(window.gtag && window.__verifikoAnalyticsConfigured);
}

function trackEvent(eventName: string, params: AnalyticsParams): boolean {
  if (!ensureAnalyticsReady()) {
    return false;
  }

  window.gtag?.("event", eventName, params);
  return true;
}

export function trackPageView({ pagePath, pageTitle, language }: PageViewParams): void {
  const trackingKey = `${pagePath}|${pageTitle}|${language}`;

  if (window.__verifikoLastPageViewKey === trackingKey) {
    return;
  }

  const didTrack = trackEvent("page_view", {
    page_path: pagePath,
    page_title: pageTitle,
    language,
  });

  if (didTrack) {
    window.__verifikoLastPageViewKey = trackingKey;
  }
}

export function trackNamedPageView({ eventName, ...context }: NamedPageViewParams): void {
  const trackingKey = `${eventName}|${context.sourcePath}|${context.language}`;
  
  if (trackedNamedPageViewKeys.has(trackingKey)) {
    return;
  }

  const didTrack = trackEvent(eventName, buildAnalyticsContext(context));

  if (didTrack) {
    trackedNamedPageViewKeys.add(trackingKey);
  }
}

export function trackAnalysisInputStarted({
  inputMethod,
  ...context
}: AnalysisInputStartedParams): void {
  trackEvent("analysis_input_started", {
    ...buildAnalyticsContext(context),
    input_method: inputMethod,
  });
}

export function trackAnalysisStarted({
  inputType,
  hasProtocol,
  ...context
}: AnalysisStartedParams): void {
  trackEvent("analysis_started", {
    ...buildAnalyticsContext(context),
    input_type: inputType,
    has_protocol: hasProtocol,
  });
}

export function trackAnalysisCompleted({
  riskLevel,
  verdict,
  signalCount,
  warningCount,
  hasFetchDegradation,
  ...context
}: AnalysisCompletedParams): void {
  trackEvent("analysis_completed", {
    ...buildAnalyticsContext(context),
    risk_level: riskLevel,
    verdict,
    signal_count: signalCount,
    warning_count: warningCount,
    has_fetch_degradation: hasFetchDegradation,
  });
}

export function trackAnalysisFailed({
  errorType,
  ...context
}: AnalysisFailedParams): void {
  trackEvent("analysis_failed", {
    ...buildAnalyticsContext(context),
    error_type: errorType,
  });
}

export function trackQuotaPromptShown({
  promptType,
  ...context
}: QuotaPromptShownParams): void {
  trackEvent("quota_prompt_shown", {
    ...buildAnalyticsContext(context),
    prompt_type: promptType,
  });
}

export function trackQuotaBlocked({
  retryAfterSeconds,
  ...context
}: QuotaBlockedParams): void {
  trackEvent("quota_blocked", {
    ...buildAnalyticsContext(context),
    retry_after_seconds: retryAfterSeconds ?? 0,
  });
}

export function trackAuthEntryClicked({
  entryPoint,
  ...context
}: AuthEntryClickedParams): void {
  trackEvent("auth_entry_clicked", {
    ...buildAnalyticsContext(context),
    entry_point: entryPoint,
  });
}

export function trackResultActionClicked({
  action,
  resultState,
  ...context
}: ResultActionClickedParams): void {
  trackEvent("result_action_clicked", {
    ...buildAnalyticsContext(context),
    action,
    result_state: resultState,
  });
}

export function trackUpgradeIntentClicked({
  source,
  ...context
}: UpgradeIntentClickedParams): void {
  trackEvent("upgrade_intent_clicked", {
    ...buildAnalyticsContext(context),
    source,
  });
}

export function categorizeAnalysisError(error: unknown): string {
  if (!(error instanceof Error)) {
    return "unknown_error";
  }

  const normalizedMessage = error.message.toLowerCase();

  if (normalizedMessage.includes("vite_api_base_url")) {
    return "configuration_error";
  }

  if (normalizedMessage.includes("failed to fetch") || normalizedMessage.includes("network")) {
    return "network_error";
  }

  if (normalizedMessage.includes("status")) {
    return "request_error";
  }

  return "unknown_error";
}

export function detectDegradedCoverage(verification: ApiVerification): boolean {
  return DEGRADED_COVERAGE_PATTERN.test(verification.risk_assessment.summary);
}
