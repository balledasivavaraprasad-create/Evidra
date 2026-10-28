import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, AUTH_REQUIRED_EVENT, type AuthUser } from "../api/client";
import { forgetWorkspaceId } from "./currentWorkspace";

type AuthStatus = "checking" | "signed-in" | "signed-out";

interface AuthContextType {
  status: AuthStatus;
  user: AuthUser | null;
  /** False on a local development backend (AUTH_MODE=local), where everyone is the local reviewer. */
  authRequired: boolean;
  googleClientId: string | null;
  /** Call after a successful sign-in or sign-up response. */
  setSignedIn: (user: AuthUser) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  status: "checking",
  user: null,
  authRequired: false,
  googleClientId: null,
  setSignedIn: () => {},
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authRequired, setAuthRequired] = useState(true);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.auth
      .session()
      .then((s) => {
        if (!mounted) return;
        setAuthRequired(s.auth_required);
        setGoogleClientId(s.google_client_id ?? null);
        setUser(s.user ?? null);
        setStatus(s.authenticated && s.user ? "signed-in" : "signed-out");
      })
      .catch(() => {
        // Service unreachable: show the sign-in page, which explains the server is waking up
        if (mounted) setStatus("signed-out");
      });

    const onAuthRequired = () => {
      setUser(null);
      setStatus("signed-out");
    };
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
    return () => {
      mounted = false;
      window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
    };
  }, []);

  const setSignedIn = useCallback((u: AuthUser) => {
    setUser(u);
    setStatus("signed-in");
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.auth.logout();
    } finally {
      forgetWorkspaceId();
      setUser(null);
      setStatus("signed-out");
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, authRequired, googleClientId, setSignedIn, signOut }),
    [status, user, authRequired, googleClientId, setSignedIn, signOut],
  );

  if (status === "checking") {
    return <div className="min-h-screen bg-[var(--bg-base)]" aria-busy="true" />;
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/** Wraps routes that need a signed-in user; others are sent to sign in and brought back after. */
export const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { status } = useAuth();
  const location = useLocation();
  if (status !== "signed-in") {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={`/signin?next=${encodeURIComponent(next)}`} replace />;
  }
  return <>{children}</>;
};

/** Only allow same-site paths as a post-sign-in destination. */
export function safeNextPath(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/signin") || raw.startsWith("/signup")) {
    return "/dashboard";
  }
  return raw;
}
