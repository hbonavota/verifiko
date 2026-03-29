import { useI18n } from "../../lib/i18n";
import { GoogleSignInButton } from "./GoogleSignInButton";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

interface EmailAuthModalProps {
  open: boolean;
  onClose: () => void;
  onAuthenticated?: () => void | Promise<void>;
}

export function EmailAuthModal({ open, onClose, onAuthenticated }: EmailAuthModalProps) {
  const { copy } = useI18n();

  if (!open) {
    return null;
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
            <GoogleSignInButton
              className="auth-modal__google"
              onSuccess={async () => {
                await onAuthenticated?.();
                onClose();
              }}
            />
          </div>

          <div className="auth-modal__support">
            <Button disabled variant="secondary">
              {copy.topbar.signInWithEmail}
            </Button>
            <p className="auth-modal__status">{copy.authModal.magicLinkComingSoon}</p>
            <div className="auth-modal__actions">
              <Button onClick={onClose} variant="ghost">
                {copy.common.close}
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
