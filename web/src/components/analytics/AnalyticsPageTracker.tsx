import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { useI18n } from "../../lib/i18n";
import { trackPageView } from "../../lib/analytics";

export function AnalyticsPageTracker() {
  const location = useLocation();
  const { language } = useI18n();

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

  return null;
}
