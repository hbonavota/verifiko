import { useEffect, useRef, useState } from "react";

import {
  applyAnalyticsConsent,
  persistAnalyticsConsentChoice,
  readAnalyticsConsentChoice,
} from "../../lib/analyticsConsent";
import { useI18n } from "../../lib/i18n";
import { Button } from "./Button";

interface CookieBannerProps {
  reopenKey?: number;
}

export function CookieBanner({ reopenKey = 0 }: CookieBannerProps) {
  const [isVisible, setIsVisible] = useState(false);
  const previousReopenKey = useRef(reopenKey);
  const { copy } = useI18n();

  useEffect(() => {
    const storedChoice = readAnalyticsConsentChoice();

    if (storedChoice) {
      applyAnalyticsConsent(storedChoice);
      return;
    }

    setIsVisible(true);
  }, []);

  useEffect(() => {
    if (reopenKey === previousReopenKey.current) {
      return;
    }

    previousReopenKey.current = reopenKey;
    setIsVisible(true);
  }, [reopenKey]);

  function handleChoice(choice: "granted" | "denied") {
    persistAnalyticsConsentChoice(choice);
    applyAnalyticsConsent(choice);
    setIsVisible(false);
  }

  if (!isVisible) {
    return null;
  }

  return (
    <aside
      aria-live="polite"
      aria-label={copy.cookieBanner.dialogLabel}
      className="cookie-banner"
      role="dialog"
    >
      <div className="cookie-banner__body">
        <p className="cookie-banner__title">{copy.cookieBanner.title}</p>
        <p className="cookie-banner__copy">{copy.cookieBanner.description}</p>
      </div>
      <div className="cookie-banner__actions">
        <Button onClick={() => handleChoice("denied")} variant="ghost">
          {copy.cookieBanner.reject}
        </Button>
        <Button onClick={() => handleChoice("granted")} variant="primary">
          {copy.cookieBanner.accept}
        </Button>
      </div>
    </aside>
  );
}
