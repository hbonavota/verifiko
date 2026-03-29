import { formatRiskLevel, formatVerdict } from "./formatVerdict";
import type { Language } from "./i18n";
import type { VerificationSummary } from "../types/verification";

interface VerificationExportLabels {
  title: string;
  target: string;
  risk: string;
  trustScore: string;
  verdict: string;
  executedAt: string;
  summary: string;
  signals: string;
  link: string;
}

type ShareVerificationResult = "shared" | "copied" | "unavailable" | "cancelled";

export function buildVerificationDetailUrl(id: string): string {
  return new URL(`/verifications/${id}`, window.location.origin).toString();
}

export function buildVerificationExportText(
  verification: VerificationSummary,
  {
    language,
    locale,
    labels,
  }: {
    language: Language;
    locale: string;
    labels: VerificationExportLabels;
  },
): string {
  const retainedSignals = verification.signals
    .slice(0, 3)
    .map(
      (signal) =>
        `- ${signal.title} (${formatRiskLevel(signal.severity, language)}): ${signal.reason}`,
    );

  return [
    `${labels.title}: ${verification.subject}`,
    `${labels.target}: ${verification.normalizedInput}`,
    `${labels.risk}: ${formatRiskLevel(verification.riskLevel, language)}`,
    `${labels.trustScore}: ${Math.round(verification.score)}/100`,
    `${labels.verdict}: ${formatVerdict(verification.verdict, language)}`,
    `${labels.executedAt}: ${new Date(verification.createdAt).toLocaleString(locale)}`,
    `${labels.summary}: ${verification.summary}`,
    retainedSignals.length > 0 ? `${labels.signals}:` : null,
    ...retainedSignals,
    `${labels.link}: ${buildVerificationDetailUrl(verification.id)}`,
  ]
    .filter((item): item is string => Boolean(item))
    .join("\n");
}

export async function copyVerificationLink(verificationId: string): Promise<boolean> {
  return copyTextToClipboard(buildVerificationDetailUrl(verificationId));
}

export async function copyVerificationSummary(
  verification: VerificationSummary,
  options: {
    language: Language;
    locale: string;
    labels: VerificationExportLabels;
  },
): Promise<boolean> {
  return copyTextToClipboard(buildVerificationExportText(verification, options));
}

export async function shareVerification(
  verification: VerificationSummary,
  {
    language,
    locale,
    labels,
  }: {
    language: Language;
    locale: string;
    labels: VerificationExportLabels;
  },
): Promise<ShareVerificationResult> {
  const url = buildVerificationDetailUrl(verification.id);
  const text = buildVerificationExportText(verification, {
    language,
    locale,
    labels,
  });

  if (typeof navigator.share === "function") {
    try {
      await navigator.share({
        title: labels.title,
        text,
        url,
      });
      return "shared";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return "cancelled";
      }
    }
  }

  return (await copyTextToClipboard(url)) ? "copied" : "unavailable";
}

async function copyTextToClipboard(value: string): Promise<boolean> {
  if (!navigator.clipboard?.writeText) {
    return false;
  }

  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}
