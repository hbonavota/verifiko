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
  fetchQuotaStatus,
  getCurrentUser,
  registerWithEmailPassword as registerWithEmailPasswordRequest,
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

  useEffect(() => {
    if (!authReady) {
      return;
    }

    setQuotaReady(false);
    void refreshQuotaStatus();
  }, [authReady, currentUser?.id, refreshQuotaStatus]);

  function applyAuthenticatedSession(accessToken: {
    access_token: string;
    token_type: string;
    user: ApiUser;
  }) {
    persistAuthSession(accessToken);
    setCurrentUser(accessToken.user);
  }

  async function loginWithGoogleCredential(idToken: string) {
    setIsAuthenticating(true);
    try {
      const session = await authenticateWithGoogle(idToken);
      applyAuthenticatedSession(session);
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function loginWithEmailPassword(email: string, password: string) {
    setIsAuthenticating(true);
    try {
      const session = await authenticateWithEmailPassword({ email, password });
      applyAuthenticatedSession(session);
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function registerWithEmailPassword(displayName: string, email: string, password: string) {
    setIsAuthenticating(true);
    try {
      const session = await registerWithEmailPasswordRequest({
        display_name: displayName,
        email,
        password,
      });
      applyAuthenticatedSession(session);
    } finally {
      setIsAuthenticating(false);
    }
  }

  function logout() {
    clearStoredAuthSession();
    setCurrentUser(null);
  }

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
      logout,
      refreshQuotaStatus,
    }),
    [
      authReady,
      currentUser,
      isAuthenticating,
      quotaReady,
      quotaStatus,
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
