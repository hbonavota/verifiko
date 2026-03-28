import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../../lib/auth";
import { useI18n } from "../../lib/i18n";
import { GoogleSignInButton } from "./GoogleSignInButton";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";

type AuthMode = "login" | "register";

interface EmailAuthModalProps {
  open: boolean;
  onClose: () => void;
  initialMode?: AuthMode;
  onAuthenticated?: () => void | Promise<void>;
}

const EMAIL_PATTERN = /^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+$/i;

export function EmailAuthModal({
  open,
  onClose,
  initialMode = "login",
  onAuthenticated,
}: EmailAuthModalProps) {
  const { copy } = useI18n();
  const { isAuthenticating, loginWithEmailPassword, registerWithEmailPassword } = useAuth();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    setMode(initialMode);
    setErrorMessage(null);
  }, [initialMode, open]);

  if (!open) {
    return null;
  }

  const modalCopy = mode === "login" ? copy.authModal.login : copy.authModal.register;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    const normalizedEmail = email.trim().toLowerCase();
    const trimmedDisplayName = displayName.trim();

    if (mode === "register" && trimmedDisplayName.length < 2) {
      setErrorMessage(copy.authModal.errors.displayNameRequired);
      return;
    }

    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setErrorMessage(copy.authModal.errors.emailInvalid);
      return;
    }

    if (mode === "register") {
      if (password.length < 8) {
        setErrorMessage(copy.authModal.errors.passwordTooShort);
        return;
      }
      if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
        setErrorMessage(copy.authModal.errors.passwordNeedsLetterAndNumber);
        return;
      }
    } else if (!password) {
      setErrorMessage(copy.authModal.errors.passwordRequired);
      return;
    }

    try {
      if (mode === "login") {
        await loginWithEmailPassword(normalizedEmail, password);
      } else {
        await registerWithEmailPassword(trimmedDisplayName, normalizedEmail, password);
      }

      setDisplayName("");
      setEmail("");
      setPassword("");
      await onAuthenticated?.();
      onClose();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : copy.topbar.authenticationFailed);
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
        eyebrow={modalCopy.eyebrow}
        title={modalCopy.title}
        description={modalCopy.description}
        className="auth-modal__panel"
        tone="success"
      >
        <div className="auth-modal__content">
          <div className="auth-modal__mode-switch" role="tablist" aria-label={copy.authModal.modeLabel}>
            <button
              className={
                mode === "login"
                  ? "auth-modal__mode-button auth-modal__mode-button--active"
                  : "auth-modal__mode-button"
              }
              onClick={() => {
                setMode("login");
                setErrorMessage(null);
              }}
              role="tab"
              type="button"
            >
              {copy.authModal.loginTab}
            </button>
            <button
              className={
                mode === "register"
                  ? "auth-modal__mode-button auth-modal__mode-button--active"
                  : "auth-modal__mode-button"
              }
              onClick={() => {
                setMode("register");
                setErrorMessage(null);
              }}
              role="tab"
              type="button"
            >
              {copy.authModal.registerTab}
            </button>
          </div>

          <form className="auth-modal__form" onSubmit={(event) => void handleSubmit(event)}>
            {mode === "register" ? (
              <Input
                autoComplete="name"
                hint={copy.authModal.register.displayNameHint}
                label={copy.authModal.displayNameLabel}
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            ) : null}
            <Input
              autoComplete="email"
              inputMode="email"
              label={copy.authModal.emailLabel}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              hint={mode === "register" ? copy.authModal.passwordHint : undefined}
              label={copy.authModal.passwordLabel}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {errorMessage ? <p className="auth-modal__error">{errorMessage}</p> : null}
            <div className="auth-modal__actions">
              <Button disabled={isAuthenticating} type="submit" variant="primary">
                {isAuthenticating ? copy.topbar.signingIn : modalCopy.submitCta}
              </Button>
              <Button onClick={onClose} variant="ghost">
                {copy.common.close}
              </Button>
            </div>
          </form>

          <div className="auth-modal__alternate">
            <p className="auth-modal__alternate-label">{copy.authModal.orContinueWithGoogle}</p>
            <GoogleSignInButton
              className="auth-modal__google"
              onSuccess={async () => {
                await onAuthenticated?.();
                onClose();
              }}
            />
          </div>
        </div>
      </Card>
    </div>
  );
}
