import { useEffect, useState } from "react";

import { applyAnalyticsConsent, persistAnalyticsConsentChoice, readAnalyticsConsentChoice } from "../../lib/analyticsConsent";
import { Button } from "./Button";

export function CookieBanner() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const storedChoice = readAnalyticsConsentChoice();

    if (storedChoice) {
      applyAnalyticsConsent(storedChoice);
      return;
    }

    setIsVisible(true);
  }, []);

  function handleChoice(choice: "granted" | "denied") {
    persistAnalyticsConsentChoice(choice);
    applyAnalyticsConsent(choice);
    setIsVisible(false);
  }

  if (!isVisible) {
    return null;
  }

  return (
    <aside aria-live="polite" className="cookie-banner" role="dialog" aria-label="Cookie consent">
      <div className="cookie-banner__body">
        <p className="cookie-banner__title">Analytics cookies</p>
        <p className="cookie-banner__copy">
          We use analytics cookies to understand site usage and improve Verifiko.
        </p>
      </div>
      <div className="cookie-banner__actions">
        <Button onClick={() => handleChoice("denied")} variant="ghost">
          Reject
        </Button>
        <Button onClick={() => handleChoice("granted")} variant="primary">
          Accept
        </Button>
      </div>
    </aside>
  );
}
