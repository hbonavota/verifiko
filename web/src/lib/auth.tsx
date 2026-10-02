import {
  useCallback,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import type { ApiQuotaStatus, ApiUser } from "../types/verification";
import {
  authenticateWithEmailPassword,
  authenticateWithGoogle,
  consumeMagicLink,
  fetchQuotaStatus,
  getCurrentUser,
  registerWithEmailPassword as registerWithEmailPasswordRequest,
  requestMagicLink as requestMagicLinkRequest,
} from "./api";
import {
  clearStoredAuthSession,
  persistAuthSession,
  readStoredAuthSession,
} from "./authSessionStorage";

interface AuthContextValue {
  authReady: boolean;
  currentUser: ApiUser | null;
  isAuthenticating: boolean;
  quotaReady: boolean;
  quotaStatus: ApiQuotaStatus | null;
  loginWithGoogleCredential: (idToken: string) => Promise<void>;
  loginWithEmailPassword: (email: string, password: string) => Promise<void>;
  registerWithEmailPassword: (
    displayName: string,
    email: string,
    password: string,
  ) => Promise<void>;
  requestMagicLink: (email: string) => Promise<void>;
  loginWithMagicLinkToken: (token: string) => Promise<void>;
  logout: () => void;
  refreshQuotaStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [authReady, setAuthReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [quotaReady, setQuotaReady] = useState(false);
  const [quotaStatus, setQuotaStatus] = useState<ApiQuotaStatus | null>(null);

  const refreshQuotaStatus = useCallback(async () => {
    if (!authReady) {
      return;
    }

    try {
      const status = await fetchQuotaStatus();
      setQuotaStatus(status);
    } catch {
      setQuotaStatus(null);
    } finally {
      setQuotaReady(true);
    }
  }, [authReady]);

  useEffect(() => {
    let isMounted = true;
    const storedSession = readStoredAuthSession();

    if (!storedSession) {
      setAuthReady(true);
      return;
    }

    void getCurrentUser()
      .then((user) => {
        if (!isMounted) {
          return;
        }

        persistAuthSession({
          access_token: storedSession.access_token,
          token_type: storedSession.token_type,
          user,
        });
        setCurrentUser(user);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }

        clearStoredAuthSession();
        setCurrentUser(null);
      })
      .finally(() => {
        if (isMounted) {
          setAuthReady(true);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // NOTE: quota-status is intentionally NOT fetched here. The landing ("/") must
  // stay API-free on first paint, so the app shell (AppLayout) triggers the
  // quota fetch on mount instead — it only ever renders inside the app.

  // Every method is wrapped in useCallback with stable deps so its identity does
  // NOT change when auth/quota state changes. Consumers (notably the imperative
  // Google button) depend on these references in effects; an unstable identity
  // made those effects re-run on every quota refresh, tearing down and rebuilding
  // the Google iframe (visible flicker + the GSI "initialize called multiple
  // times" warning).
  const applyAuthenticatedSession = useCallback(
    (accessToken: { access_token: string; token_type: string; user: ApiUser }) => {
      persistAuthSession(accessToken);
      setCurrentUser(accessToken.user);
    },
    [],
  );

  const loginWithGoogleCredential = useCallback(
    async (idToken: string) => {
      setIsAuthenticating(true);
      try {
        applyAuthenticatedSession(await authenticateWithGoogle(idToken));
      } finally {
        setIsAuthenticating(false);
      }
    },
    [applyAuthenticatedSession],
  );

  const loginWithEmailPassword = useCallback(
    async (email: string, password: string) => {
      setIsAuthenticating(true);
      try {
        applyAuthenticatedSession(await authenticateWithEmailPassword({ email, password }));
      } finally {
        setIsAuthenticating(false);
      }
    },
    [applyAuthenticatedSession],
  );

  const registerWithEmailPassword = useCallback(
    async (displayName: string, email: string, password: string) => {
      setIsAuthenticating(true);
      try {
        applyAuthenticatedSession(
          await registerWithEmailPasswordRequest({
            display_name: displayName,
            email,
            password,
          }),
        );
      } finally {
        setIsAuthenticating(false);
      }
    },
    [applyAuthenticatedSession],
  );

  const requestMagicLink = useCallback(async (email: string) => {
    await requestMagicLinkRequest(email);
  }, []);

  const loginWithMagicLinkToken = useCallback(
    async (token: string) => {
      setIsAuthenticating(true);
      try {
        applyAuthenticatedSession(await consumeMagicLink(token));
      } finally {
        setIsAuthenticating(false);
      }
    },
    [applyAuthenticatedSession],
  );

  const logout = useCallback(() => {
    clearStoredAuthSession();
    setCurrentUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authReady,
      currentUser,
      isAuthenticating,
      quotaReady,
      quotaStatus,
      loginWithGoogleCredential,
      loginWithEmailPassword,
      registerWithEmailPassword,
      requestMagicLink,
      loginWithMagicLinkToken,
      logout,
      refreshQuotaStatus,
    }),
    [
      authReady,
      currentUser,
      isAuthenticating,
      quotaReady,
      quotaStatus,
      loginWithGoogleCredential,
      loginWithEmailPassword,
      registerWithEmailPassword,
      requestMagicLink,
      loginWithMagicLinkToken,
      logout,
      refreshQuotaStatus,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
