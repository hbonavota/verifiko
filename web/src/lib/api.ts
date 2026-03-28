import type {
  ApiAuthSession,
  ApiUser,
  ApiVerification,
  CreateVerificationInput,
  HealthCheckResult,
} from "../types/verification";
import { readStoredAuthSession } from "./authSessionStorage";
import { getStoredLanguage, type Language } from "./i18n";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE_URL =
  configuredApiBaseUrl && configuredApiBaseUrl.length > 0
    ? configuredApiBaseUrl.replace(/\/+$/, "")
    : import.meta.env.DEV
      ? "http://localhost:8000"
      : "";

function getRequiredApiBaseUrl(): string {
  const language = getStoredLanguage();

  if (!API_BASE_URL) {
    throw new Error(
      language === "es"
        ? "VITE_API_BASE_URL no está configurado."
        : "VITE_API_BASE_URL is not configured.",
    );
  }

  return API_BASE_URL;
}

export class ApiRequestError extends Error {
  status: number;
  retryAfterSeconds: number | null;

  constructor(message: string, status: number, retryAfterSeconds: number | null = null) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const language = getStoredLanguage();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  headers.set("Accept-Language", language);
  const storedSession = readStoredAuthSession();
  if (storedSession?.access_token && !headers.has("Authorization")) {
    headers.set(
      "Authorization",
      `${storedSession.token_type} ${storedSession.access_token}`,
    );
  }

  const response = await fetch(`${getRequiredApiBaseUrl()}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail =
      language === "es"
        ? `La solicitud falló con el estado ${response.status}.`
        : `Request failed with status ${response.status}.`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep the status-based error when the response is not JSON.
    }

    const retryAfterHeader = response.headers.get("Retry-After");
    const retryAfterSeconds =
      retryAfterHeader && /^\d+$/.test(retryAfterHeader)
        ? Number.parseInt(retryAfterHeader, 10)
        : null;

    throw new ApiRequestError(detail, response.status, retryAfterSeconds);
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

export function authenticateWithGoogle(idToken: string): Promise<ApiAuthSession> {
  return readJson<ApiAuthSession>("/api/auth/google", {
    method: "POST",
    body: JSON.stringify({ id_token: idToken }),
  });
}

export function getCurrentUser(): Promise<ApiUser> {
  return readJson<ApiUser>("/api/me");
}

export function getOwnedVerificationById(verificationId: string): Promise<ApiVerification> {
  return readJson<ApiVerification>(`/api/verifications/${verificationId}`);
}

export function listMyVerifications(limit = 20, offset = 0): Promise<ApiVerification[]> {
  return readJson<ApiVerification[]>(`/api/me/verifications?limit=${limit}&offset=${offset}`);
}
