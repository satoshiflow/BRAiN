"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchCurrentUser,
  isUnauthorizedAuthError,
  login as loginRequest,
  logout as logoutRequest,
  refreshAccessToken,
  type AuthenticatedUser,
} from "@/lib/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

const E2E_BYPASS_AUTH = process.env.NEXT_PUBLIC_AXE_E2E_BYPASS_AUTH === "true";
const AUTH_STORAGE_KEY = "axe.auth.session.v1";

type PersistedAuthState = {
  accessToken: string;
  refreshToken: string;
  user: AuthenticatedUser;
};

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
  const refreshInFlightRef = useRef<Promise<PersistedAuthState> | null>(null);

  const persistAuthState = useCallback((next: PersistedAuthState | null) => {
    if (typeof window === "undefined") {
      return;
    }

    if (!next) {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(next));
  }, []);

  const restorePersistedAuthState = useCallback((): PersistedAuthState | null => {
    if (typeof window === "undefined") {
      return null;
    }

    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    try {
      const parsed = JSON.parse(raw) as Partial<PersistedAuthState>;
      if (!parsed.accessToken || !parsed.refreshToken || !parsed.user) {
        return null;
      }
      return {
        accessToken: parsed.accessToken,
        refreshToken: parsed.refreshToken,
        user: parsed.user,
      };
    } catch {
      return null;
    }
  }, []);

  const clearAuthState = useCallback(() => {
    setStatus("unauthenticated");
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    persistAuthState(null);
  }, [persistAuthState]);

  useEffect(() => {
    if (process.env.NODE_ENV === "test" || E2E_BYPASS_AUTH) {
      return;
    }

    const hydrateSession = async () => {
      const persisted = restorePersistedAuthState();
      if (!persisted) {
        clearAuthState();
        return;
      }

      setStatus("loading");
      try {
        const profile = await fetchCurrentUser(persisted.accessToken);
        setAccessToken(persisted.accessToken);
        setRefreshToken(persisted.refreshToken);
        setUser(profile);
        setStatus("authenticated");
        persistAuthState({
          accessToken: persisted.accessToken,
          refreshToken: persisted.refreshToken,
          user: profile,
        });
      } catch (error) {
        if (!isUnauthorizedAuthError(error)) {
          clearAuthState();
          return;
        }

        try {
          const refreshed = await refreshAccessToken(persisted.refreshToken);
          const profile = await fetchCurrentUser(refreshed.access_token);
          setAccessToken(refreshed.access_token);
          setRefreshToken(refreshed.refresh_token);
          setUser(profile);
          setStatus("authenticated");
          persistAuthState({
            accessToken: refreshed.access_token,
            refreshToken: refreshed.refresh_token,
            user: profile,
          });
        } catch {
          clearAuthState();
        }
      }
    };

    void hydrateSession();
  }, [clearAuthState, persistAuthState, restorePersistedAuthState]);

  const login = useCallback(async (email: string, password: string) => {
    setStatus("loading");
    try {
      const pair = await loginRequest({ email, password });
      const profile = await fetchCurrentUser(pair.access_token);

      setAccessToken(pair.access_token);
      setRefreshToken(pair.refresh_token);
      setUser(profile);
      setStatus("authenticated");
      persistAuthState({
        accessToken: pair.access_token,
        refreshToken: pair.refresh_token,
        user: profile,
      });
    } catch (error) {
      clearAuthState();
      throw error;
    }
  }, [clearAuthState, persistAuthState]);

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

  const ensureRefreshedSession = useCallback(
    async (token: string): Promise<PersistedAuthState> => {
      if (!refreshInFlightRef.current) {
        refreshInFlightRef.current = (async () => {
          const refreshed = await refreshAccessToken(token);
          const refreshedProfile = await fetchCurrentUser(refreshed.access_token);
          const nextState: PersistedAuthState = {
            accessToken: refreshed.access_token,
            refreshToken: refreshed.refresh_token,
            user: refreshedProfile,
          };

          setAccessToken(nextState.accessToken);
          setRefreshToken(nextState.refreshToken);
          setUser(nextState.user);
          setStatus("authenticated");
          persistAuthState(nextState);

          return nextState;
        })()
          .catch((refreshError) => {
            clearAuthState();
            throw refreshError;
          })
          .finally(() => {
            refreshInFlightRef.current = null;
          });
      }

      return refreshInFlightRef.current;
    },
    [clearAuthState, persistAuthState]
  );

  const withAuthRetry = useCallback(
    async <T,>(request: (token: string) => Promise<T>): Promise<T> => {
      if (!accessToken) {
        throw new Error("Authentication required");
      }

      try {
        return await request(accessToken);
      } catch (error) {
        if (!isUnauthorizedAuthError(error) || !refreshToken) {
          throw error;
        }

        try {
          const refreshedSession = await ensureRefreshedSession(refreshToken);
          return request(refreshedSession.accessToken);
        } catch (refreshError) {
          throw refreshError;
        }
      }
    },
    [accessToken, ensureRefreshedSession, refreshToken]
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
