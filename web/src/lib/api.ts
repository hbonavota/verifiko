import type {
  ApiVerification,
  CreateVerificationInput,
  HealthCheckResult,
} from "../types/verification";
import type { Language } from "./i18n";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE_URL =
  configuredApiBaseUrl && configuredApiBaseUrl.length > 0
    ? configuredApiBaseUrl.replace(/\/+$/, "")
    : import.meta.env.DEV
      ? "http://localhost:8000"
      : "";

function getRequiredApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  return API_BASE_URL;
}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getRequiredApiBaseUrl()}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep the status-based error when the response is not JSON.
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function fetchApiHealth(language: Language = "en"): Promise<HealthCheckResult> {
  const payload = await readJson<{ status: string }>("/health");

  return {
    status: payload.status === "ok" ? "ok" : "error",
    checkedAt: new Date().toISOString(),
    detail:
      payload.status === "ok"
        ? language === "es"
          ? "El backend es accesible y responde a la sonda de estado."
          : "Backend is reachable and responding to the health probe."
        : language === "es"
          ? "El backend respondió, pero la carga de estado fue inesperada."
          : "Backend responded, but the health payload was unexpected.",
  };
}

export function getApiBaseUrl(language: Language = "en"): string {
  return API_BASE_URL || (language === "es" ? "Sin configurar" : "Not configured");
}

export function createVerification(input: CreateVerificationInput): Promise<ApiVerification> {
  return readJson<ApiVerification>("/api/verifications", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getVerificationById(verificationId: string): Promise<ApiVerification> {
  return readJson<ApiVerification>(`/api/verifications/${verificationId}`);
}

export function listVerifications(): Promise<ApiVerification[]> {
  return readJson<ApiVerification[]>("/api/verifications");
}
