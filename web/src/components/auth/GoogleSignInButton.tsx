import { useEffect, useRef, useState } from "react";

import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";

const GOOGLE_IDENTITY_SCRIPT_SELECTOR = 'script[data-google-identity="true"]';
const GOOGLE_IDENTITY_SCRIPT_SRC = "https://accounts.google.com/gsi/client";
const GOOGLE_IDENTITY_LOAD_TIMEOUT_MS = 10_000;
// GIS exposes no "popup blocked" callback (initialize's callback fires only on
// success), so a blocked or abandoned popup is inferred from window focus.
const POPUP_FOCUS_CHECK_MS = 1200;
const POPUP_RETURN_GRACE_MS = 1500;
// Production must set the same OAuth web client ID in both the web and API projects.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim() ?? "";

let googleIdentityScriptPromise: Promise<void> | null = null;
let hasLoggedMissingClientId = false;
let hasLoggedInitializationFailure = false;

// google.accounts.id.initialize() must run only once for the whole app —
// calling it per button (and on every re-render) triggers the GSI "initialized
// multiple times" warning. Initialize once and route the credential to whichever
// button is currently mounted via a shared handler.
let googleIdentityInitialized = false;
let activeGoogleCredentialHandler: ((credential: string) => void) | null = null;

function ensureGoogleIdentityInitialized(): void {
  if (googleIdentityInitialized || !window.google?.accounts?.id) {
    return;
  }
  window.google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: (response) => {
      if (response.credential) {
        activeGoogleCredentialHandler?.(response.credential);
      }
    },
    ux_mode: "popup",
    auto_select: false,
    cancel_on_tap_outside: true,
  });
  googleIdentityInitialized = true;
}

interface GoogleSignInButtonProps {
  className?: string;
  onSuccess?: () => void | Promise<void>;
  onInteraction?: () => void;
  variant?: "default" | "quota";
  busy?: boolean;
  busyLabel?: string;
}

export function GoogleSignInButton({
  className,
  onInteraction,
  onSuccess,
  variant = "default",
  busy = false,
  busyLabel,
}: GoogleSignInButtonProps) {
  const { copy, language } = useI18n();
  const { isAuthenticating, loginWithGoogleCredential } = useAuth();
  const buttonRef = useRef<HTMLDivElement | null>(null);
  const credentialHandlerRef = useRef<((credential: string) => void) | null>(null);
  // Set by the popup-detection effect; called when a credential arrives so a
  // pending "popup blocked/closed" check never fires over a real sign-in.
  const cancelPopupCheckRef = useRef<(() => void) | null>(null);
  const [runtimeErrorMessage, setRuntimeErrorMessage] = useState<string | null>(null);
  const [showPopupNotice, setShowPopupNotice] = useState(false);
  const busyState = busy || isAuthenticating;
  const variantClassName = variant === "quota" ? "google-sign-in--quota" : "";
  const rootClassName = [
    "google-sign-in",
    variantClassName,
    busyState ? "google-sign-in--busy" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const configurationErrorMessage = !GOOGLE_CLIENT_ID
    ? copy.topbar.googleSignInNotConfigured
    : null;
  const errorMessage = configurationErrorMessage ?? runtimeErrorMessage;

  // Keep the credential-handling logic in a ref. Updating it (when auth or
  // onSuccess change) must NOT re-run the render effect below — that would tear
  // down and rebuild the Google iframe (flicker + the GSI "initialize called
  // multiple times" warning). The rendered button always routes through this ref.
  useEffect(() => {
    credentialHandlerRef.current = (credential: string) => {
      cancelPopupCheckRef.current?.();
      void loginWithGoogleCredential(credential)
        .then(async () => {
          setRuntimeErrorMessage(null);
          setShowPopupNotice(false);
          await onSuccess?.();
        })
        .catch((error) => {
          setRuntimeErrorMessage(
            error instanceof Error ? error.message : copy.topbar.authenticationFailed,
          );
        });
    };
  }, [copy.topbar.authenticationFailed, loginWithGoogleCredential, onSuccess]);

  // Popup-blocked inference. The button is a cross-origin iframe, so clicks never
  // reach React: a click shows up as the window losing focus to that iframe. If
  // the page still has focus shortly after (no popup took it), the popup was
  // blocked. If a popup did take focus and the page gets it back without a
  // credential, the popup was closed. Own effect with no deps, so it never
  // re-runs the render effect below (that would rebuild the GIS iframe).
  useEffect(() => {
    let armed = false;
    let focusCheckTimer: number | undefined;
    let returnGraceTimer: number | undefined;

    function clearTimers() {
      window.clearTimeout(focusCheckTimer);
      window.clearTimeout(returnGraceTimer);
    }

    function disarm() {
      armed = false;
      clearTimers();
    }

    function showNotice() {
      disarm();
      setShowPopupNotice(true);
    }

    function handleBlur() {
      const host = buttonRef.current;
      const active = document.activeElement;
      if (!host || !(active instanceof HTMLIFrameElement) || !host.contains(active)) {
        return;
      }
      disarm();
      armed = true;
      setShowPopupNotice(false);
      focusCheckTimer = window.setTimeout(() => {
        if (armed && document.hasFocus()) {
          showNotice();
        }
      }, POPUP_FOCUS_CHECK_MS);
    }

    function handleFocus() {
      if (!armed) {
        return;
      }
      clearTimers();
      returnGraceTimer = window.setTimeout(() => {
        if (armed) {
          showNotice();
        }
      }, POPUP_RETURN_GRACE_MS);
    }

    cancelPopupCheckRef.current = disarm;
    window.addEventListener("blur", handleBlur);
    window.addEventListener("focus", handleFocus);
    return () => {
      window.removeEventListener("blur", handleBlur);
      window.removeEventListener("focus", handleFocus);
      clearTimers();
      cancelPopupCheckRef.current = null;
    };
  }, []);

  useEffect(() => {
    const host = buttonRef.current;
    if (!host || configurationErrorMessage) {
      if (configurationErrorMessage && !hasLoggedMissingClientId) {
        console.error(
          "[GoogleSignInButton] VITE_GOOGLE_CLIENT_ID is not configured. Google Sign-In is disabled.",
        );
        hasLoggedMissingClientId = true;
      }
      return;
    }

    let isCancelled = false;

    function renderButton() {
      if (!window.google?.accounts?.id || !host || isCancelled) {
        return;
      }

      // This button becomes the active credential target while it is mounted; it
      // routes to the ref, which always holds the latest handler.
      activeGoogleCredentialHandler = (credential) => credentialHandlerRef.current?.(credential);
      ensureGoogleIdentityInitialized();
      host.replaceChildren();
      window.google.accounts.id.renderButton(host, {
        theme: variant === "quota" ? "filled_black" : "outline",
        size: variant === "quota" ? "large" : "medium",
        shape: "pill",
        text: "continue_with",
        locale: language === "es" ? "es" : "en",
      });
    }

    void ensureGoogleIdentityScript()
      .then(() => {
        if (isCancelled) {
          return;
        }

        setRuntimeErrorMessage(null);
        renderButton();
      })
      .catch((error) => {
        if (isCancelled) {
          return;
        }

        if (!hasLoggedInitializationFailure) {
          console.error("[GoogleSignInButton] Failed to initialize Google Sign-In.", error);
          hasLoggedInitializationFailure = true;
        }
        setRuntimeErrorMessage(copy.topbar.googleSignInUnavailable);
      });

    return () => {
      isCancelled = true;
    };
    // Deliberately narrow: the iframe is (re)rendered only when the locale, the
    // variant, or the config-error state changes — never on auth/quota updates.
  }, [configurationErrorMessage, copy.topbar.googleSignInUnavailable, language, variant]);

  return (
    <div className={rootClassName}>
      {errorMessage ? (
        <button
          aria-label={copy.topbar.signInWithGoogle}
          className="google-sign-in__fallback"
          disabled
          type="button"
        >
          {copy.topbar.signInWithGoogle}
        </button>
      ) : (
        <div
          aria-label={copy.topbar.signInWithGoogle}
          className="google-sign-in__button"
          onClickCapture={onInteraction}
          ref={buttonRef}
        />
      )}
      {busyState ? (
        <p className="google-sign-in__hint">{busyLabel ?? copy.topbar.signingIn}</p>
      ) : null}
      {errorMessage ? <p className="google-sign-in__error">{errorMessage}</p> : null}
      {showPopupNotice && !errorMessage ? (
        <p className="google-sign-in__hint google-sign-in__notice" role="status">
          {copy.topbar.googlePopupBlocked}
        </p>
      ) : null}
    </div>
  );
}

function ensureGoogleIdentityScript(): Promise<void> {
  if (window.google?.accounts?.id) {
    return Promise.resolve();
  }

  if (!googleIdentityScriptPromise) {
    googleIdentityScriptPromise = new Promise<void>((resolve, reject) => {
      const existingScript = document.querySelector<HTMLScriptElement>(
        GOOGLE_IDENTITY_SCRIPT_SELECTOR,
      );
      const script = existingScript ?? document.createElement("script");

      if (!existingScript) {
        script.async = true;
        script.defer = true;
        script.dataset.googleIdentity = "true";
        script.src = GOOGLE_IDENTITY_SCRIPT_SRC;
        document.head.appendChild(script);
      }

      const timeoutId = window.setTimeout(() => {
        cleanup();
        reject(new Error("Google Identity Services did not initialize before timeout."));
      }, GOOGLE_IDENTITY_LOAD_TIMEOUT_MS);

      const intervalId = window.setInterval(() => {
        if (!window.google?.accounts?.id) {
          return;
        }

        cleanup();
        resolve();
      }, 50);

      function handleError() {
        cleanup();
        reject(new Error("Google Identity Services failed to load."));
      }

      function cleanup() {
        window.clearInterval(intervalId);
        window.clearTimeout(timeoutId);
        script.removeEventListener("error", handleError);
      }

      script.addEventListener("error", handleError, { once: true });
    }).catch((error) => {
      googleIdentityScriptPromise = null;
      throw error;
    });
  }

  return googleIdentityScriptPromise;
}
