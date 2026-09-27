import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, errorMessage, setUnauthorizedHandler, tokenStore, type User } from "../api/client";

interface AuthState {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const loadMe = useCallback(async () => {
    const { data } = await api.GET("/api/auth/me");
    setUser(data ?? null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    loadMe().finally(() => setLoading(false));
  }, [loadMe]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { data, error } = await api.POST("/api/auth/login", {
        body: { username: email, password, scope: "" },
        bodySerializer: (b) => new URLSearchParams(b as Record<string, string>),
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      if (!data) throw new Error(errorMessage(error, "Incorrect email or password."));
      tokenStore.set(data.access_token);
      await loadMe();
    },
    [loadMe],
  );

  const value = useMemo(() => ({ user, loading, signIn, signOut }), [user, loading, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
