import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, AUTH_REQUIRED_EVENT } from "../api/client";
import { LoginScreen } from "../features/auth/LoginScreen";

type AuthState = "checking" | "open" | "locked";

interface AuthContextType {
  /** True when this deployment asks for the site password (AUTH_MODE=password). */
  authRequired: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({ authRequired: false, signOut: async () => {} });

export const useAuth = () => useContext(AuthContext);

/**
 * Shows the password screen when the backend runs with AUTH_MODE=password and this
 * browser has no valid session. Everywhere else (local development, backend offline)
 * the app renders normally and pages show their own offline messages.
 */
export const AuthGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>("checking");
  const [authRequired, setAuthRequired] = useState(false);

  useEffect(() => {
    let mounted = true;
    api.auth
      .session()
      .then((s) => {
        if (!mounted) return;
        setAuthRequired(s.auth_required);
        setState(s.auth_required && !s.authenticated ? "locked" : "open");
      })
      .catch(() => {
        // Backend unreachable or an older backend without the gate: let pages explain
        if (mounted) setState("open");
      });

    const onAuthRequired = () => {
      setAuthRequired(true);
      setState("locked");
    };
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
    return () => {
      mounted = false;
      window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
    };
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.auth.logout();
    } finally {
      setState("locked");
    }
  }, []);

  const onSignedIn = useCallback(() => {
    // Reload so every page fetches its data with the new session
    window.location.reload();
  }, []);

  if (state === "checking") {
    return <div className="min-h-screen bg-[var(--bg-base)]" aria-busy="true" />;
  }

  if (state === "locked") {
    return <LoginScreen onSignedIn={onSignedIn} />;
  }

  return <AuthContext.Provider value={{ authRequired, signOut }}>{children}</AuthContext.Provider>;
};
