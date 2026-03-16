export type Tone = "neutral" | "primary" | "success" | "warning" | "danger";

export function toneForRiskLevel(riskLevel: string): Tone {
  if (riskLevel === "SAFE" || riskLevel === "LOW") {
    return "success";
  }

  if (riskLevel === "MEDIUM") {
    return "warning";
  }

  if (riskLevel === "HIGH" || riskLevel === "CRITICAL") {
    return "danger";
  }

  return "neutral";
}
