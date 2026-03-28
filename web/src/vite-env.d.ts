/// <reference types="vite/client" />

interface Window {
  __verifikoAnalyticsConfigured?: boolean;
  __verifikoLastPageViewKey?: string;
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
}
