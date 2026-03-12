import { getApiBase } from "@/lib/config";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string | null;
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText || `Auth error ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function login(credentials: LoginCredentials): Promise<TokenPair> {
  return authRequest<TokenPair>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthenticatedUser> {
  return authRequest<AuthenticatedUser>("/api/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenPair> {
  return authRequest<TokenPair>("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logout(refreshToken: string): Promise<void> {
  const response = await fetch(`${getApiBase()}/api/auth/logout`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });

  if (!response.ok && response.status !== 204) {
    const text = await response.text();
    throw new Error(text || response.statusText || `Logout error ${response.status}`);
  }
}
