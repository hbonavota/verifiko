import { useCallback, useState, type FormEvent } from "react";

import { ApiRequestError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";
import { GoogleSignInButton } from "./GoogleSignInButton";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";

interface EmailAuthModalProps {
  open: boolean;
  onClose: () => void;
  onAuthenticated?: () => void | Promise<void>;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type RequestStatus = "idle" | "submitting" | "sent" | "error";

export function EmailAuthModal({ open, onClose, onAuthenticated }: EmailAuthModalProps) {
  const { copy } = useI18n();
  const { requestMagicLink } = useAuth();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<RequestStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Stable across email keystrokes so the Google button effect never re-runs and
  // re-renders (which caused the button to flicker/resize while typing).
  const handleGoogleSuccess = useCallback(async () => {
    await onAuthenticated?.();
    onClose();
  }, [onAuthenticated, onClose]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim();
    if (!EMAIL_PATTERN.test(trimmedEmail)) {
      setStatus("error");
      setErrorMessage(copy.authModal.errors.emailInvalid);
      return;
    }

    setStatus("submitting");
    setErrorMessage(null);
    try {
      await requestMagicLink(trimmedEmail);
      setStatus("sent");
    } catch (error) {
      setStatus("error");
      if (error instanceof ApiRequestError && error.status === 429) {
        setErrorMessage(copy.authModal.errors.rateLimited);
      } else {
        setErrorMessage(copy.authModal.errors.requestFailed);
      }
    }
  }

  return (
    <div
      className="auth-modal"
      role="dialog"
      aria-label={copy.authModal.dialogLabel}
      aria-modal="true"
    >
      <button
        aria-label={copy.common.close}
        className="auth-modal__backdrop"
        onClick={onClose}
        type="button"
      />
      <Card
        eyebrow={copy.authModal.eyebrow}
        title={copy.authModal.title}
        description={copy.authModal.description}
        className="auth-modal__panel"
        tone="success"
      >
        <div className="auth-modal__content">
          <div className="auth-modal__alternate">
            <p className="auth-modal__alternate-label">{copy.authModal.googlePrompt}</p>
            <GoogleSignInButton className="auth-modal__google" onSuccess={handleGoogleSuccess} />
          </div>

          <div className="auth-modal__support">
            {status === "sent" ? (
              <div className="auth-modal__status-panel" role="status">
                <p className="auth-modal__status-title">{copy.authModal.linkSentTitle}</p>
                <p className="auth-modal__status">{copy.authModal.linkSentCopy}</p>
                <div className="auth-modal__actions">
                  <Button onClick={() => setStatus("idle")} variant="secondary">
                    {copy.authModal.resend}
                  </Button>
                  <Button onClick={onClose} variant="ghost">
                    {copy.common.close}
                  </Button>
                </div>
              </div>
            ) : (
              <form className="auth-modal__email-form" onSubmit={handleSubmit}>
                <p className="auth-modal__alternate-label">{copy.authModal.emailPrompt}</p>
                <Input
                  label={copy.authModal.emailLabel}
                  hint={copy.authModal.emailHint}
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={status === "submitting"}
                />
                {errorMessage ? (
                  <p className="auth-modal__status auth-modal__status--error" role="alert">
                    {errorMessage}
                  </p>
                ) : null}
                <div className="auth-modal__actions">
                  <Button type="submit" disabled={status === "submitting"}>
                    {status === "submitting"
                      ? copy.authModal.emailSubmitting
                      : copy.authModal.emailSubmitCta}
                  </Button>
                  <Button onClick={onClose} variant="ghost" type="button">
                    {copy.common.close}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
