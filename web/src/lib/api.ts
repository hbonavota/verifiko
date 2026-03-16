import type { HealthCheckResult } from "../types/verification";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchApiHealth(): Promise<HealthCheckResult> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}.`);
  }

  const payload = (await response.json()) as { status: string };

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
  return API_BASE_URL;
}

