import { getApiBase } from "@/lib/config";

export class AuthApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string, fallbackMessage?: string) {
    super(body || fallbackMessage || `Auth error ${status}`);
    this.name = "AuthApiError";
    this.status = status;
    this.body = body;
  }
}

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

export interface PasswordRecoveryRequestResponse {
  accepted: boolean;
  message: string;
  reset_token?: string | null;
}

export interface PasswordResetResponse {
  success: boolean;
  message: string;
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
    throw new AuthApiError(response.status, text, response.statusText);
  }

  return response.json() as Promise<T>;
}

export function isUnauthorizedAuthError(error: unknown): boolean {
  if (error instanceof AuthApiError) {
    return error.status === 401;
  }

  if (!(error instanceof Error)) {
    return false;
  }

  const message = error.message.toLowerCase();
  return message.includes("401") || message.includes("unauthorized");
}

export async function login(credentials: LoginCredentials): Promise<TokenPair> {
  return authRequest<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthenticatedUser> {
  return authRequest<AuthenticatedUser>("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenPair> {
  return authRequest<TokenPair>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logout(refreshToken: string): Promise<void> {
  const response = await fetch(`${getApiBase()}/auth/logout`, {
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
    throw new AuthApiError(response.status, text, response.statusText);
  }
}

export async function requestPasswordRecovery(email: string): Promise<PasswordRecoveryRequestResponse> {
  return authRequest<PasswordRecoveryRequestResponse>("/auth/password-recovery/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, newPassword: string): Promise<PasswordResetResponse> {
  return authRequest<PasswordResetResponse>("/auth/password-recovery/reset", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}
