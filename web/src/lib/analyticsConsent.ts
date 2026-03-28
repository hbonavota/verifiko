export const ANALYTICS_MEASUREMENT_ID = "G-PP4YXR4F10";
export const ANALYTICS_CONSENT_STORAGE_KEY = "verifiko.analytics-consent";

export type AnalyticsConsentChoice = "granted" | "denied";

export function readAnalyticsConsentChoice(): AnalyticsConsentChoice | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const value = window.localStorage.getItem(ANALYTICS_CONSENT_STORAGE_KEY);
    return value === "granted" || value === "denied" ? value : null;
  } catch {
    return null;
  }
}

export function persistAnalyticsConsentChoice(choice: AnalyticsConsentChoice): void {
  try {
    window.localStorage.setItem(ANALYTICS_CONSENT_STORAGE_KEY, choice);
  } catch {
    // Ignore storage failures and keep the in-memory consent update.
  }
}

export function applyAnalyticsConsent(choice: AnalyticsConsentChoice): void {
  window.gtag?.("consent", "update", {
    analytics_storage: choice,
  });

  if (choice === "granted" && !window.__verifikoAnalyticsConfigured) {
    window.gtag?.("config", ANALYTICS_MEASUREMENT_ID);
    window.__verifikoAnalyticsConfigured = true;
  }
}
