import { useEffect, useRef, useState } from "react";

import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim() ?? "";

interface GoogleSignInButtonProps {
  className?: string;
  onSuccess?: () => void | Promise<void>;
  variant?: "default" | "quota";
  busy?: boolean;
  busyLabel?: string;
}

export function GoogleSignInButton({
  className,
  onSuccess,
  variant = "default",
  busy = false,
  busyLabel,
}: GoogleSignInButtonProps) {
  const { copy, language } = useI18n();
  const { isAuthenticating, loginWithGoogleCredential } = useAuth();
  const buttonRef = useRef<HTMLDivElement | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const busyState = busy || isAuthenticating;
  const variantClassName = variant === "quota" ? "google-sign-in--quota" : "";
  const rootClassName = ["google-sign-in", variantClassName, busyState ? "google-sign-in--busy" : "", className]
    .filter(Boolean)
    .join(" ");

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
            .then(async () => {
              setErrorMessage(null);
              await onSuccess?.();
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
        theme: variant === "quota" ? "filled_black" : "outline",
        size: variant === "quota" ? "large" : "medium",
        shape: "pill",
        text: variant === "quota" ? "continue_with" : "signin_with",
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
  }, [copy.topbar.authenticationFailed, language, loginWithGoogleCredential, onSuccess, variant]);

  if (!GOOGLE_CLIENT_ID) {
    return null;
  }

  return (
    <div className={rootClassName}>
      <div
        aria-label={copy.topbar.signInWithGoogle}
        className="google-sign-in__button"
        ref={buttonRef}
      />
      {busyState ? (
        <p className="google-sign-in__hint">{busyLabel ?? copy.topbar.signingIn}</p>
      ) : null}
      {errorMessage ? <p className="google-sign-in__error">{errorMessage}</p> : null}
    </div>
  );
}
