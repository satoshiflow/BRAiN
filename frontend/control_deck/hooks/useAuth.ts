/**
 * Authentication hooks for Control Deck
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

// ============================================================================
// Types
// ============================================================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserInfo {
  username: string;
  email: string | null;
  full_name: string | null;
  roles: string[];
  is_admin: boolean;
}

// ============================================================================
// Token Storage
// ============================================================================

const TOKEN_KEY = "brain_auth_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeStoredToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getStoredToken();
}

// ============================================================================
// API Client with Auth
// ============================================================================

function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://localhost:8000";

async function authenticatedRequest<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };

  const options: RequestInit = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    if (response.status === 401) {
      // Unauthorized - clear token
      removeStoredToken();
    }
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Get current user information
 */
export function useCurrentUser() {
  return useQuery<UserInfo>({
    queryKey: ["auth", "me"],
    queryFn: () => authenticatedRequest<UserInfo>("GET", "/api/auth/me"),
    enabled: isAuthenticated(),
    retry: false,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Login with username and password
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation<Token, Error, LoginRequest>({
    mutationKey: ["auth", "login"],
    mutationFn: (credentials: LoginRequest) =>
      apiPost<Token>("/api/auth/login/json", credentials),
    onSuccess: (data) => {
      setStoredToken(data.access_token);
      queryClient.invalidateQueries({ queryKey: ["auth"] });
    },
  });
}

/**
 * Logout (clears token)
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["auth", "logout"],
    mutationFn: async () => {
      removeStoredToken();
    },
    onSuccess: () => {
      queryClient.clear();
    },
  });
}
