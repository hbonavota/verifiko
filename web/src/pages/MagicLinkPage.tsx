import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";

type MagicLinkStatus = "verifying" | "success" | "invalid" | "missing";

export function MagicLinkPage() {
  const { copy } = useI18n();
  const { loginWithMagicLinkToken } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<MagicLinkStatus>("verifying");
  const startedRef = useRef(false);

  useDocumentMeta(copy.magicLink.metaTitle);

  const token = searchParams.get("token");

  useEffect(() => {
    if (startedRef.current) {
      return;
    }
    startedRef.current = true;

    if (!token) {
      setStatus("missing");
      return;
    }

    let active = true;
    void loginWithMagicLinkToken(token)
      .then(() => {
        if (!active) {
          return;
        }
        setStatus("success");
        window.setTimeout(() => navigate("/dashboard", { replace: true }), 600);
      })
      .catch(() => {
        if (active) {
          setStatus("invalid");
        }
      });

    return () => {
      active = false;
    };
    // Depend only on the token. loginWithMagicLinkToken is recreated on every
    // auth-context render, and a successful exchange updates that context — so
    // including it here re-runs this effect, whose cleanup flips `active` to
    // false and swallows the success state, leaving the page stuck on
    // "Signing you in…". startedRef already guarantees the exchange runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const message =
    status === "verifying"
      ? copy.magicLink.verifying
      : status === "success"
        ? copy.magicLink.success
        : status === "missing"
          ? copy.magicLink.missingToken
          : copy.magicLink.invalidToken;

  const showRetry = status === "invalid" || status === "missing";

  return (
    <PageShell>
      <div className="auth-status" role="status" aria-live="polite">
        <div className={`auth-status__indicator auth-status__indicator--${status}`} aria-hidden="true">
          {status === "verifying" ? (
            <span className="auth-status__spinner" />
          ) : status === "success" ? (
            <svg viewBox="0 0 24 24" fill="none" width="30" height="30">
              <path
                d="M5 12.5l4 4 10-10"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" width="30" height="30">
              <path d="M12 7v6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
              <circle cx="12" cy="16.5" r="1.15" fill="currentColor" />
            </svg>
          )}
        </div>
        <p className="section-title__eyebrow">Verifiko</p>
        <h1 className="auth-status__title">{message}</h1>
        {status === "success" ? (
          <p className="auth-status__hint">{copy.magicLink.redirecting}</p>
        ) : null}
        {showRetry ? (
          <Button to="/" variant="secondary">
            {copy.magicLink.backHome}
          </Button>
        ) : null}
      </div>
    </PageShell>
  );
}
