import { useEffect, useState } from "react";

import { useI18n } from "../../lib/i18n";

/**
 * Staged progress shown while a verification runs. The verification itself is a
 * single synchronous request, so the stages advance on a timed cadence that
 * roughly matches a typical run — the stages themselves are the real pipeline
 * steps. The final stage keeps spinning until the result arrives (this component
 * unmounts), so a slower run never looks "stuck".
 */
export function VerificationProgress() {
  const { copy } = useI18n();
  const stages: readonly string[] = copy.home.progressStages;
  const [completed, setCompleted] = useState(0);

  useEffect(() => {
    setCompleted(0);
    const timers: number[] = [];
    // Tick each stage (except the last) to "done" in sequence; the last one
    // stays active until the request resolves and this unmounts.
    for (let i = 1; i < stages.length; i += 1) {
      timers.push(window.setTimeout(() => setCompleted(i), i * 620));
    }
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [stages.length]);

  return (
    <div className="verify-progress" role="status" aria-live="polite">
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
      <p className="verify-progress__hint">{copy.home.progressTimeHint}</p>
    </div>
  );
}
