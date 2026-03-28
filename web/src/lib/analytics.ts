import { applyAnalyticsConsent, readAnalyticsConsentChoice } from "./analyticsConsent";
import type { ApiVerification } from "../types/verification";

const DEGRADED_COVERAGE_PATTERN =
  /analysis coverage degraded|cobertura de análisis degradada|cobertura de analisis degradada/i;

type AnalyticsParams = Record<string, string | number | boolean>;

interface PageViewParams {
  pagePath: string;
  pageTitle: string;
  language: string;
}

interface AnalysisStartedParams {
  sourcePage: string;
  language: string;
  inputType: "manual" | "paste";
  hasProtocol: boolean;
}

interface AnalysisCompletedParams {
  sourcePage: string;
  language: string;
  riskLevel: string;
  verdict: string;
  signalCount: number;
  warningCount: number;
  hasFetchDegradation: boolean;
}

interface AnalysisFailedParams {
  sourcePage: string;
  language: string;
  errorType: string;
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

export function trackAnalysisStarted({
  sourcePage,
  language,
  inputType,
  hasProtocol,
}: AnalysisStartedParams): void {
  trackEvent("analysis_started", {
    source_page: sourcePage,
    language,
    input_type: inputType,
    has_protocol: hasProtocol,
  });
}

export function trackAnalysisCompleted({
  sourcePage,
  language,
  riskLevel,
  verdict,
  signalCount,
  warningCount,
  hasFetchDegradation,
}: AnalysisCompletedParams): void {
  trackEvent("analysis_completed", {
    source_page: sourcePage,
    language,
    risk_level: riskLevel,
    verdict,
    signal_count: signalCount,
    warning_count: warningCount,
    has_fetch_degradation: hasFetchDegradation,
  });
}

export function trackAnalysisFailed({
  sourcePage,
  language,
  errorType,
}: AnalysisFailedParams): void {
  trackEvent("analysis_failed", {
    source_page: sourcePage,
    language,
    error_type: errorType,
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
  return DEGRADED_COVERAGE_PATTERN.test(verification.risk_assessment?.summary ?? "");
}
