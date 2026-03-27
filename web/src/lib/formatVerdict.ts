import type { Language } from "./i18n";

export function formatVerdict(verdict: string, language: Language = "en") {
  const normalizedVerdict = verdict.replace(/_/g, " ").replace(/\s+/g, " ").trim().toUpperCase();

  if (normalizedVerdict === "TRUSTED" || normalizedVerdict === "SAFE") {
    return language === "es" ? "Seguro" : "Safe";
  }

  if (normalizedVerdict === "CAUTION" || normalizedVerdict === "SUSPICIOUS" || normalizedVerdict === "NEEDS REVIEW") {
    return language === "es" ? "Sospechoso" : "Suspicious";
  }

  if (normalizedVerdict === "LIKELY MALICIOUS" || normalizedVerdict === "CONFIRMED MALICIOUS") {
    return language === "es" ? "Malicioso" : "Malicious";
  }

  return normalizedVerdict
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function formatRiskLevel(riskLevel: string, language: Language = "en") {
  const normalizedRiskLevel = riskLevel.trim().toUpperCase();

  const riskLevelLabels = {
    SAFE: language === "es" ? "Seguro" : "Safe",
    LOW: language === "es" ? "Bajo" : "Low",
    MEDIUM: language === "es" ? "Medio" : "Medium",
    HIGH: language === "es" ? "Alto" : "High",
    CRITICAL: language === "es" ? "Crítico" : "Critical",
  } as const;

  return riskLevelLabels[normalizedRiskLevel as keyof typeof riskLevelLabels] ?? normalizedRiskLevel;
}

export function formatVerificationStatus(status: string, language: Language = "en") {
  const normalizedStatus = status.trim().toUpperCase();

  const statusLabels = {
    PENDING: language === "es" ? "Pendiente" : "Pending",
    ANALYZING: language === "es" ? "Analizando" : "Analyzing",
    COMPLETED: language === "es" ? "Completado" : "Completed",
    FAILED: language === "es" ? "Fallido" : "Failed",
  } as const;

  return statusLabels[normalizedStatus as keyof typeof statusLabels] ?? normalizedStatus;
}
