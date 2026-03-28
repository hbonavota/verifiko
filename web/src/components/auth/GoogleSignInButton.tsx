import { useEffect, useRef, useState } from "react";

import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim() ?? "";

export function GoogleSignInButton() {
  const { copy, language } = useI18n();
  const { isAuthenticating, loginWithGoogleCredential } = useAuth();
  const buttonRef = useRef<HTMLDivElement | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const host = buttonRef.current;
    if (!host || !GOOGLE_CLIENT_ID) {
      return;
    }

    function renderButton() {
      if (!window.google?.accounts?.id || !host) {
        return;
      }

      host.replaceChildren();
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response) => {
          if (!response.credential) {
            return;
          }

          void loginWithGoogleCredential(response.credential)
            .then(() => {
              setErrorMessage(null);
            })
            .catch((error) => {
              setErrorMessage(
                error instanceof Error ? error.message : copy.topbar.authenticationFailed,
              );
            });
        },
        ux_mode: "popup",
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      window.google.accounts.id.renderButton(host, {
        theme: "outline",
        size: "medium",
        shape: "pill",
        text: "signin_with",
        locale: language === "es" ? "es" : "en",
      });
    }

    if (window.google?.accounts?.id) {
      renderButton();
      return;
    }

    const script = document.querySelector<HTMLScriptElement>('script[data-google-identity="true"]');
    if (!script) {
      return;
    }

    script.addEventListener("load", renderButton);
    return () => {
      script.removeEventListener("load", renderButton);
    };
  }, [copy.topbar.authenticationFailed, language, loginWithGoogleCredential]);

  if (!GOOGLE_CLIENT_ID) {
    return null;
  }

  return (
    <div className="topbar-auth">
      <div
        aria-label={copy.topbar.signInWithGoogle}
        className="topbar-auth__google-button"
        ref={buttonRef}
      />
      {isAuthenticating ? <p className="topbar-auth__hint">{copy.topbar.signingIn}</p> : null}
      {errorMessage ? <p className="topbar-auth__error">{errorMessage}</p> : null}
    </div>
  );
}
