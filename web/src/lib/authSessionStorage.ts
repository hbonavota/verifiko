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

// Plan of the saved session while it is still being validated, or null when there
// is none. Used by the topbar and sidebar restore placeholders; storage can throw
// (private mode, blocked site data), which reads as "no saved session".
export function readPendingSessionPlan(): string | null {
  try {
    const session = readStoredAuthSession();
    return session ? session.user?.plan ?? "FREE" : null;
  } catch {
    return null;
  }
}

export function clearStoredAuthSession(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}
