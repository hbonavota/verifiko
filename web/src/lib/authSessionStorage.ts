import type { ApiAuthSession } from "../types/verification";

const STORAGE_KEY = "verifiko-auth-session";

export function readStoredAuthSession(): ApiAuthSession | null {
  const rawValue = window.localStorage.getItem(STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as ApiAuthSession;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function persistAuthSession(session: ApiAuthSession): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredAuthSession(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}
