/**
 * React Query hooks for Authentication
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

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

export interface User {
  username: string;
  email: string | null;
  full_name: string | null;
  disabled: boolean;
  roles: string[];
}

export interface CreateUserRequest {
  username: string;
  password: string;
  email?: string;
  full_name?: string;
  roles?: string[];
}

export interface RoleInfo {
  name: string;
  display_name: string;
  description: string;
  permissions: string[];
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

  const response = await fetch(`${process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://localhost:8000"}${path}`, options);

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

/**
 * List all users (admin only)
 */
export function useUsers() {
  return useQuery<User[]>({
    queryKey: ["auth", "users"],
    queryFn: () => authenticatedRequest<User[]>("GET", "/api/auth/users"),
    enabled: isAuthenticated(),
  });
}

/**
 * Get available roles
 */
export function useRoles() {
  return useQuery<{ roles: RoleInfo[] }>({
    queryKey: ["auth", "roles"],
    queryFn: () => api.get<{ roles: RoleInfo[] }>("/api/auth/roles"),
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
      api.post<Token>("/api/auth/login/json", credentials),
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

/**
 * Refresh access token
 */
export function useRefreshToken() {
  const queryClient = useQueryClient();

  return useMutation<Token, Error>({
    mutationKey: ["auth", "refresh"],
    mutationFn: () => authenticatedRequest<Token>("POST", "/api/auth/refresh"),
    onSuccess: (data) => {
      setStoredToken(data.access_token);
      queryClient.invalidateQueries({ queryKey: ["auth"] });
    },
  });
}

/**
 * Create a new user (admin only)
 */
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation<User, Error, CreateUserRequest>({
    mutationKey: ["auth", "create-user"],
    mutationFn: (request: CreateUserRequest) =>
      authenticatedRequest<User>("POST", "/api/auth/users", request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "users"] });
    },
  });
}

/**
 * Delete a user (admin only)
 */
export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationKey: ["auth", "delete-user"],
    mutationFn: (username: string) =>
      authenticatedRequest<void>("DELETE", `/api/auth/users/${username}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "users"] });
    },
  });
}
