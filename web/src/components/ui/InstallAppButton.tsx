import { useEffect, useId, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { trackInstallPromptClicked } from "../../lib/analytics";
import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";
import { useInstallPrompt } from "../../lib/useInstallPrompt";

function InstallIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none">
      <path d="M12 4v10m0 0-4-4m4 4 4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 16v2.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

// The iOS Share glyph (square with an arrow out of the top).
function ShareIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" className="install-app__share-icon">
      <path d="M12 3v11m0-11-3.5 3.5M12 3l3.5 3.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8 10H6.5A1.5 1.5 0 0 0 5 11.5v8A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5v-8a1.5 1.5 0 0 0-1.5-1.5H16" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function InstallAppButton() {
  const { copy, language } = useI18n();
  const { currentUser, quotaStatus } = useAuth();
  const location = useLocation();
  const { mode, promptInstall } = useInstallPrompt();
  const [showIosSteps, setShowIosSteps] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const stepsId = useId();

  useEffect(() => {
    if (!showIosSteps) {
      return;
    }
    function close(event: Event) {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !rootRef.current?.contains(event.target as Node)) {
        setShowIosSteps(false);
      }
    }
    document.addEventListener("keydown", close);
    document.addEventListener("pointerdown", close);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("pointerdown", close);
    };
  }, [showIosSteps]);

  if (mode === "hidden") {
    return null;
  }

  function handleClick() {
    trackInstallPromptClicked({
      sourcePath: location.pathname,
      language,
      isAuthenticated: Boolean(currentUser),
      plan: currentUser?.plan ?? quotaStatus?.plan ?? "ANONYMOUS",
      platform: mode === "ios" ? "ios" : "native",
    });
    if (mode === "ios") {
      setShowIosSteps((open) => !open);
      return;
    }
    void promptInstall();
  }

  return (
    <div className="install-app" ref={rootRef}>
      {/* Same markup as <Button variant="ghost" leadingIcon>, which can't pass the
          aria attributes the iOS popover needs. */}
      <button
        aria-controls={mode === "ios" ? stepsId : undefined}
        aria-expanded={mode === "ios" ? showIosSteps : undefined}
        className="button button--ghost install-app__button"
        onClick={handleClick}
        type="button"
      >
        <span className="button__icon">
          <InstallIcon />
        </span>
        <span>{copy.landing.installApp}</span>
      </button>
      {mode === "ios" && showIosSteps ? (
        <div className="install-app__steps" id={stepsId} role="note">
          <ShareIcon />
          <p>{copy.landing.installIosSteps}</p>
        </div>
      ) : null}
    </div>
  );
}
