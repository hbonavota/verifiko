/// <reference types="vite/client" />

interface Window {
  __verifikoAnalyticsConfigured?: boolean;
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
}
