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
  }, [token, loginWithMagicLinkToken, navigate]);

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
      <div className="section-title section-title--center">
        <p className="section-title__eyebrow">Verifiko</p>
        <h1 className="section-title__heading">{message}</h1>
      </div>
      {showRetry ? (
        <Button to="/" variant="secondary">
          {copy.magicLink.backHome}
        </Button>
      ) : null}
    </PageShell>
  );
}
