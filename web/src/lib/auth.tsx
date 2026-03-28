import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import type { ApiUser } from "../types/verification";
import { authenticateWithGoogle, getCurrentUser } from "./api";
import {
  clearStoredAuthSession,
  persistAuthSession,
  readStoredAuthSession,
} from "./authSessionStorage";

interface AuthContextValue {
  authReady: boolean;
  currentUser: ApiUser | null;
  isAuthenticating: boolean;
  loginWithGoogleCredential: (idToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [authReady, setAuthReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

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

  async function loginWithGoogleCredential(idToken: string) {
    setIsAuthenticating(true);
    try {
      const session = await authenticateWithGoogle(idToken);
      persistAuthSession(session);
      setCurrentUser(session.user);
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
      loginWithGoogleCredential,
      logout,
    }),
    [authReady, currentUser, isAuthenticating],
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
