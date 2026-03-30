import { getApiBase } from "@/lib/config";

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

  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
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
