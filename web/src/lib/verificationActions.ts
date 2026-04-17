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
  const riskAssessment = verification.riskAssessment;
  const retainedSignals = verification.signals
    .slice(0, 3)
    .map(
      (signal) =>
        `- ${signal.title} (${formatRiskLevel(signal.severity, language)}): ${signal.description}`,
    );

  return [
    `${labels.title}: ${verification.originalInput}`,
    `${labels.target}: ${verification.normalizedInput}`,
    `${labels.risk}: ${formatRiskLevel(riskAssessment.riskLevel, language)}`,
    `${labels.trustScore}: ${Math.round(riskAssessment.score)}/100`,
    `${labels.verdict}: ${formatVerdict(riskAssessment.verdict, language)}`,
    `${labels.executedAt}: ${new Date(verification.createdAt).toLocaleString(locale)}`,
    `${labels.summary}: ${riskAssessment.summary}`,
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
