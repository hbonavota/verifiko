import { useEffect, useState } from "react";

import { Button } from "./Button";
import { Card } from "./Card";
import { useI18n } from "../../lib/i18n";
import { type UpgradeIntentSource, useUpgradeIntent } from "../../lib/upgradeIntentStorage";

interface UpgradeModalProps {
  open: boolean;
  onClose: () => void;
  source?: UpgradeIntentSource;
}

type UpgradeModalView = "default" | "submitted" | "saved";

export function UpgradeModal({ open, onClose, source = "topbar" }: UpgradeModalProps) {
  const { copy } = useI18n();
  const { hasSubmittedUpgradeIntent, saveUpgradeIntent } = useUpgradeIntent();
  const [view, setView] = useState<UpgradeModalView>("default");

  useEffect(() => {
    if (!open) {
      return;
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect -- resets the modal view each time it opens
    setView(hasSubmittedUpgradeIntent ? "saved" : "default");
  }, [hasSubmittedUpgradeIntent, open]);

  if (!open) {
    return null;
  }

  const modalCopy =
    view === "submitted"
      ? copy.upgradeModal.submitted
      : view === "saved"
        ? copy.upgradeModal.saved
        : copy.upgradeModal.default;

  return (
    <div
      className="upgrade-modal"
      role="dialog"
      aria-label={copy.upgradeModal.dialogLabel}
      aria-modal="true"
    >
      <button
        aria-label={copy.common.close}
        className="upgrade-modal__backdrop"
        onClick={onClose}
        type="button"
      />
      <Card
        eyebrow={modalCopy.eyebrow}
        title={modalCopy.title}
        description={modalCopy.description}
        className="upgrade-modal__panel"
        tone="success"
      >
        <div className="upgrade-modal__content">
          {"intro" in modalCopy ? <p className="upgrade-modal__intro">{modalCopy.intro}</p> : null}
          {"points" in modalCopy ? (
            <div className="upgrade-modal__points">
              {modalCopy.points.map((point) => (
                <article key={point} className="upgrade-modal__point">
                  <p className="upgrade-modal__point-copy">{point}</p>
                </article>
              ))}
            </div>
          ) : null}
          {"supportingCopy" in modalCopy ? (
            <p className="upgrade-modal__supporting-copy">{modalCopy.supportingCopy}</p>
          ) : null}
          <div className="upgrade-modal__actions">
            {view === "default" ? (
              <Button
                onClick={() => {
                  saveUpgradeIntent(source);
                  setView("submitted");
                }}
                variant="primary"
              >
                {modalCopy.primaryCta}
              </Button>
            ) : (
              <Button onClick={onClose} variant="primary">
                {modalCopy.primaryCta}
              </Button>
            )}
            <Button onClick={onClose} variant="ghost">
              {modalCopy.secondaryCta}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
