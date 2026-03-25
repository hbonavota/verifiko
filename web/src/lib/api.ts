import type {
  ApiVerification,
  CreateVerificationInput,
  HealthCheckResult,
} from "../types/verification";

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

export async function fetchApiHealth(): Promise<HealthCheckResult> {
  const payload = await readJson<{ status: string }>("/health");

  return {
    status: payload.status === "ok" ? "ok" : "error",
    checkedAt: new Date().toISOString(),
    detail:
      payload.status === "ok"
        ? "Backend is reachable and responding to the health probe."
        : "Backend responded, but the health payload was unexpected.",
  };
}

export function getApiBaseUrl(): string {
  return API_BASE_URL || "Not configured";
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
