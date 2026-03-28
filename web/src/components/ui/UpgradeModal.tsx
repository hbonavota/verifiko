import { Button } from "./Button";
import { Card } from "./Card";
import { useI18n } from "../../lib/i18n";

interface UpgradeModalProps {
  open: boolean;
  onClose: () => void;
}

export function UpgradeModal({ open, onClose }: UpgradeModalProps) {
  const { copy } = useI18n();

  if (!open) {
    return null;
  }

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
        eyebrow={copy.upgradeModal.eyebrow}
        title={copy.upgradeModal.title}
        description={copy.upgradeModal.description}
        className="upgrade-modal__panel"
        tone="success"
      >
        <div className="upgrade-modal__content">
          <p className="upgrade-modal__intro">{copy.upgradeModal.intro}</p>
          <div className="upgrade-modal__points">
            {copy.upgradeModal.points.map((point) => (
              <article key={point} className="upgrade-modal__point">
                <p className="upgrade-modal__point-copy">{point}</p>
              </article>
            ))}
          </div>
          <div className="upgrade-modal__actions">
            <Button onClick={onClose} variant="primary">
              {copy.upgradeModal.comingSoon}
            </Button>
            <Button onClick={onClose} variant="ghost">
              {copy.common.close}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
