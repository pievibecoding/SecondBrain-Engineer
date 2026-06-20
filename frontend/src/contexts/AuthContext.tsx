import { createContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { clearCorrelationId, getToken, setCorrelationId, setToken } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  currentUser: User | null;
  loading: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const USER_KEY = "secondbrain.user";

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) as User : null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setCorrelationId(sessionStorage.getItem("secondbrain.correlation_id") || undefined);
  }, []);

  useEffect(() => {
    let active = true;

    const validateSession = async () => {
      if (!currentUser || !getToken()) {
        return;
      }
      try {
        await authApi.me();
      } catch {
        if (!active) {
          return;
        }
        setToken(null);
        sessionStorage.removeItem(USER_KEY);
        clearCorrelationId();
        setCorrelationId();
        setCurrentUser(null);
      }
    };

    void validateSession();
    return () => {
      active = false;
    };
  }, [currentUser]);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await authApi.login(email, password);
      setToken(response.access_token);
      sessionStorage.setItem(USER_KEY, JSON.stringify(response.user));
      setCurrentUser(response.user);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    sessionStorage.removeItem(USER_KEY);
    clearCorrelationId();
    setCorrelationId();
    setCurrentUser(null);
  };

  const value = useMemo<AuthContextValue>(() => ({
    currentUser,
    loading,
    isAdmin: currentUser?.role === "admin",
    login,
    logout
  }), [currentUser, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
