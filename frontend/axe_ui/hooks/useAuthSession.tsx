"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  refreshAccessToken,
  type AuthenticatedUser,
} from "@/lib/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

const E2E_BYPASS_AUTH = process.env.NEXT_PUBLIC_AXE_E2E_BYPASS_AUTH === "true";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthenticatedUser | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  getAuthHeaders: () => Record<string, string> | undefined;
  withAuthRetry: <T>(request: (accessToken: string) => Promise<T>) => Promise<T>;
};

const AuthSessionContext = createContext<AuthContextValue | null>(null);

export function AuthSessionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>(
    process.env.NODE_ENV === "test" || E2E_BYPASS_AUTH ? "authenticated" : "unauthenticated"
  );
  const [user, setUser] = useState<AuthenticatedUser | null>(
    process.env.NODE_ENV === "test" || E2E_BYPASS_AUTH
      ? {
          id: "test-user",
          email: "test@brain.local",
          username: "test-user",
          full_name: "Test User",
          role: "admin",
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
          last_login: new Date().toISOString(),
        }
      : null
  );
  const [accessToken, setAccessToken] = useState<string | null>(
    process.env.NODE_ENV === "test" || E2E_BYPASS_AUTH ? "test-access-token" : null
  );
  const [refreshToken, setRefreshToken] = useState<string | null>(
    process.env.NODE_ENV === "test" || E2E_BYPASS_AUTH ? "test-refresh-token" : null
  );

  const clearAuthState = useCallback(() => {
    setStatus("unauthenticated");
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setStatus("loading");
    try {
      const pair = await loginRequest({ email, password });
      const profile = await fetchCurrentUser(pair.access_token);

      setAccessToken(pair.access_token);
      setRefreshToken(pair.refresh_token);
      setUser(profile);
      setStatus("authenticated");
    } catch (error) {
      clearAuthState();
      throw error;
    }
  }, [clearAuthState]);

  const logout = useCallback(async () => {
    try {
      if (refreshToken) {
        await logoutRequest(refreshToken);
      }
    } catch {
      // Always clear local auth state even if backend logout fails.
    } finally {
      clearAuthState();
    }
  }, [clearAuthState, refreshToken]);

  const withAuthRetry = useCallback(
    async <T,>(request: (token: string) => Promise<T>): Promise<T> => {
      if (!accessToken) {
        throw new Error("Authentication required");
      }

      try {
        return await request(accessToken);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Request failed";
        const isUnauthorized = message.includes("401") || message.toLowerCase().includes("unauthorized");
        if (!isUnauthorized || !refreshToken) {
          throw error;
        }

        try {
          const refreshed = await refreshAccessToken(refreshToken);
          setAccessToken(refreshed.access_token);
          setRefreshToken(refreshed.refresh_token);

          const refreshedProfile = await fetchCurrentUser(refreshed.access_token);
          setUser(refreshedProfile);
          setStatus("authenticated");

          return request(refreshed.access_token);
        } catch (refreshError) {
          clearAuthState();
          throw refreshError;
        }
      }
    },
    [accessToken, clearAuthState, refreshToken]
  );

  const getAuthHeaders = useCallback(() => {
    if (!accessToken) {
      return undefined;
    }

    return {
      Authorization: `Bearer ${accessToken}`,
    };
  }, [accessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      accessToken,
      login,
      logout,
      getAuthHeaders,
      withAuthRetry,
    }),
    [accessToken, getAuthHeaders, login, logout, status, user, withAuthRetry]
  );

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession(): AuthContextValue {
  const context = useContext(AuthSessionContext);
  if (!context) {
    throw new Error("useAuthSession must be used inside AuthSessionProvider");
  }

  return context;
}
