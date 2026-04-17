import type { VerificationSignal, VerificationSummary } from "../types/verification";

export const CONTENT_VARIATION_SIGNAL_TYPE = "content_variation_detected";

export function findContentVariationSignal(
  verification: Pick<VerificationSummary, "signals">,
): VerificationSignal | undefined {
  return verification.signals.find(
    (signal) => signal.detected && signal.signalType === CONTENT_VARIATION_SIGNAL_TYPE,
  );
}
