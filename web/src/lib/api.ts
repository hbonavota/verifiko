import type {
  ApiAuthSession,
  ApiQuotaStatus,
  ApiUser,
  ApiVerification,
  CreateVerificationInput,
  EmailLoginInput,
  EmailRegistrationInput,
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
    headers.set("Authorization", `${storedSession.token_type} ${storedSession.access_token}`);
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
      const payload = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>;
      };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        const messages = payload.detail
          .map((item) => item.msg?.trim())
          .filter((message): message is string => !!message);
        if (messages.length > 0) {
          detail = messages.join(" ");
        }
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

// Returns the raw status only; the page localizes the detail text at render time,
// so switching language never repeats the request.
export async function fetchApiHealth(): Promise<HealthCheckResult> {
  const payload = await readJson<{ status: string }>("/health");

  return {
    status: payload.status === "ok" ? "ok" : "error",
    checkedAt: new Date().toISOString(),
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

export interface ApiScanAccepted {
  scan_id: string;
  status: string;
  url: string;
}

export interface ApiScanResponse {
  scan_id: string;
  status: string;
  url: string;
  created_at: string;
  updated_at: string;
  result_verification_id: string | null;
  result: ApiVerification | null;
  error: string | null;
  screenshot_url: string | null;
}

/** Submit a URL for asynchronous deep analysis (detonation). Requires auth. */
export function submitScan(input: CreateVerificationInput): Promise<ApiScanAccepted> {
  return readJson<ApiScanAccepted>("/api/v1/scans", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/** Poll a single scan by id. */
export function getScan(scanId: string): Promise<ApiScanResponse> {
  return readJson<ApiScanResponse>(`/api/v1/scans/${encodeURIComponent(scanId)}`);
}

interface RunDeepScanOptions {
  onStatus?: (status: string, attempt: number) => void;
  intervalMs?: number;
  maxAttempts?: number;
  signal?: AbortSignal;
}

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort() {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

/**
 * Submit a deep scan and poll until it completes, returning the resulting
 * verification (which carries `screenshot_url` and behavioral signals). Throws
 * ApiRequestError on failure or timeout.
 */
export async function runDeepScan(
  input: CreateVerificationInput,
  options: RunDeepScanOptions = {},
): Promise<ApiVerification> {
  const { onStatus, intervalMs = 3000, maxAttempts = 20, signal } = options;
  const language = getStoredLanguage();
  const failedMessage =
    language === "es"
      ? "No pudimos completar el análisis profundo. Prueba de nuevo."
      : "We couldn't complete the deep analysis. Please try again.";
  const timeoutMessage =
    language === "es"
      ? "El análisis profundo está tardando más de lo normal. Prueba de nuevo en un momento."
      : "The deep analysis is taking longer than usual. Please try again shortly.";

  const accepted = await submitScan(input);
  onStatus?.(accepted.status, 0);

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    await delay(intervalMs, signal);
    const scan = await getScan(accepted.scan_id);
    onStatus?.(scan.status, attempt);

    if (scan.status === "completed") {
      if (!scan.result) {
        throw new ApiRequestError(failedMessage, 502);
      }
      // Ensure the presigned screenshot URL is present on the result even if the
      // presenter did not inline it.
      return { ...scan.result, screenshot_url: scan.result.screenshot_url ?? scan.screenshot_url };
    }
    if (scan.status === "failed") {
      throw new ApiRequestError(failedMessage, 502);
    }
  }

  throw new ApiRequestError(timeoutMessage, 504);
}

export function authenticateWithGoogle(idToken: string): Promise<ApiAuthSession> {
  return readJson<ApiAuthSession>("/api/auth/google", {
    method: "POST",
    body: JSON.stringify({ id_token: idToken }),
  });
}

export function registerWithEmailPassword(input: EmailRegistrationInput): Promise<ApiAuthSession> {
  return readJson<ApiAuthSession>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function authenticateWithEmailPassword(input: EmailLoginInput): Promise<ApiAuthSession> {
  return readJson<ApiAuthSession>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function requestMagicLink(email: string): Promise<{ status: string }> {
  return readJson<{ status: string }>("/api/auth/magic-link/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function consumeMagicLink(token: string): Promise<ApiAuthSession> {
  return readJson<ApiAuthSession>("/api/auth/magic-link/consume", {
    method: "POST",
    body: JSON.stringify({ token }),
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

export function fetchQuotaStatus(): Promise<ApiQuotaStatus> {
  return readJson<ApiQuotaStatus>("/api/verifications/quota-status", {
    method: "GET",
  });
}
