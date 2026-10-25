import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";
import { trackNamedPageView, trackPageView } from "../../lib/analytics";

export function AnalyticsPageTracker() {
  const location = useLocation();
  const { authReady, currentUser, quotaStatus } = useAuth();
  const { language } = useI18n();

  const plan = currentUser?.plan ?? quotaStatus?.plan ?? "ANONYMOUS";
  const isAuthenticated = Boolean(currentUser);

  /**
   * 🔹 1. Page view REAL (navegación)
   * NO depende de auth ni plan
   */
  useEffect(() => {
    const frameId = window.requestAnimationFrame(() => {
      trackPageView({
        pagePath: location.pathname,
        pageTitle: document.title,
        language,
      });
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [language, location.pathname]);

  /**
   * 🔹 2. Named page view (contexto de producto)
   * SÍ depende de auth/plan
   */
  useEffect(() => {
    if (!authReady) {
      return;
    }

    if (location.pathname === "/") {
      trackNamedPageView({
        eventName: "verify_page_view",
        language,
        sourcePath: location.pathname,
        isAuthenticated,
        plan,
      });
    } else if (location.pathname === "/dashboard") {
      trackNamedPageView({
        eventName: "review_page_view",
        language,
        sourcePath: location.pathname,
        isAuthenticated,
        plan,
      });
    } else if (location.pathname === "/api-health") {
      trackNamedPageView({
        eventName: "status_page_view",
        language,
        sourcePath: location.pathname,
        isAuthenticated,
        plan,
      });
    }
  }, [authReady, isAuthenticated, language, location.pathname, plan]);

  return null;
}
