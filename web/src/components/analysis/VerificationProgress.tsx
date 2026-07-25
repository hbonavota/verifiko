import { useEffect, useState } from "react";

import { useI18n } from "../../lib/i18n";

interface VerificationProgressProps {
  /**
   * Deep analysis (async detonation) takes ~15–20s and has its own pipeline
   * stages, so the cadence is slower and the copy reflects the live sandbox run.
   */
  deep?: boolean;
}

/**
 * Staged progress shown while a verification runs. The request resolves on its
 * own timeline, so the stages advance on a timed cadence that roughly matches a
 * typical run — the stages themselves are the real pipeline steps. The final
 * stage keeps spinning until the result arrives (this component unmounts), so a
 * slower run never looks "stuck".
 */
export function VerificationProgress({ deep = false }: VerificationProgressProps) {
  const { copy } = useI18n();
  const stages: readonly string[] = deep
    ? copy.home.deepProgressStages
    : copy.home.progressStages;
  const hint = deep ? copy.home.deepProgressTimeHint : copy.home.progressTimeHint;
  // Deep analysis loads the page live, so give each stage more breathing room.
  const stepMs = deep ? 3200 : 620;
  const [completed, setCompleted] = useState(0);

  useEffect(() => {
    setCompleted(0);
    const timers: number[] = [];
    // Tick each stage (except the last) to "done" in sequence; the last one
    // stays active until the request resolves and this unmounts.
    for (let i = 1; i < stages.length; i += 1) {
      timers.push(window.setTimeout(() => setCompleted(i), i * stepMs));
    }
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [stages.length, stepMs]);

  return (
    <div
      className={`verify-progress${deep ? " verify-progress--deep" : ""}`}
      role="status"
      aria-live="polite"
    >
      <ol className="verify-progress__list">
        {stages.map((stage, index) => {
          const status = index < completed ? "done" : index === completed ? "active" : "pending";
          return (
            <li key={stage} className={`verify-progress__item verify-progress__item--${status}`}>
              <span className="verify-progress__marker" aria-hidden="true" />
              <span className="verify-progress__label">{stage}</span>
            </li>
          );
        })}
      </ol>
      <p className="verify-progress__hint">{hint}</p>
    </div>
  );
}
