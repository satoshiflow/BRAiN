import { getApiBase } from "@/lib/config";

function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem("access_token");
}

function hasAuthorizationHeader(headers?: HeadersInit): boolean {
  if (!headers) {
    return false;
  }

  if (headers instanceof Headers) {
    return headers.has("Authorization");
  }

  if (Array.isArray(headers)) {
    return headers.some(([key]) => key.toLowerCase() === "authorization");
  }

  return Object.keys(headers).some((key) => key.toLowerCase() === "authorization");
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string, fallbackMessage?: string) {
    super(body || fallbackMessage || `API error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  useProxy = true
): Promise<T> {
  const apiBase = getApiBase();
  const url = useProxy ? path : `${apiBase}${path}`;
  const accessToken = getStoredAccessToken();

  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  headers.set("Content-Type", "application/json");

  if (accessToken && !hasAuthorizationHeader(init?.headers)) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
    credentials: "include",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text, response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function fetchJson<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function postJson<T, B = unknown>(
  path: string,
  body: B,
  customHeaders?: Record<string, string>
): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: customHeaders,
  });
}

export async function putJson<T, B = unknown>(
  path: string,
  body: B,
  customHeaders?: Record<string, string>
): Promise<T> {
  return apiRequest<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
    headers: customHeaders,
  });
}

export async function deleteRequest<T>(
  path: string,
  customHeaders?: Record<string, string>
): Promise<T> {
  return apiRequest<T>(path, {
    method: "DELETE",
    headers: customHeaders,
  });
}

export function createEventSource(path: string): EventSource {
  const apiBase = getApiBase();
  const url = `${apiBase}${path}`;
  return new EventSource(url, { withCredentials: true });
}
