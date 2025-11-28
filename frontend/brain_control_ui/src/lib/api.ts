// frontend/brain_control_ui/src/lib/api.ts
// Zentrale, generische Fetch-API für das BRAiN Control Deck

export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

export interface ApiRequestOptions<B = any> {
  method?: HttpMethod;
  body?: B;
  headers?: Record<string, string>;
}

/**
 * Basis-URL für das BRAiN Backend.
 * Fällt bei fehlender ENV auf http://localhost:8000 zurück.
 */
export const API_BASE: string = (
  process.env.NEXT_PUBLIC_BRAIN_API_BASE_URL ??
  process.env.NEXT_PUBLIC_BRAIN_API_BASE ??
  "http://localhost:8000"
).replace(/\/+$/, "");

/**
 * Low-Level Request Helper
 */
async function request<TResponse = unknown, B = any>(
  path: string,
  { method = "GET", body, headers }: ApiRequestOptions<B> = {},
): Promise<TResponse> {
  const url = `${API_BASE}${path}`;

  const init: RequestInit = {
    method,
    headers: {
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(headers ?? {}),
    },
  };

  if (body !== undefined) {
    (init as any).body = JSON.stringify(body);
  }

  const resp = await fetch(url, init);

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${method} ${path} → HTTP ${resp.status}: ${text}`);
  }

  if (resp.status === 204) {
    // No Content
    return undefined as TResponse;
  }

  const data = (await resp.json()) as TResponse;
  return data;
}

/* ------------------------------------------------------------------
   Convenience-Funktionen (für direkte Nutzung)
-------------------------------------------------------------------*/

export function apiGet<TResponse = unknown>(path: string): Promise<TResponse> {
  return request<TResponse>(path, { method: "GET" });
}

export function apiPost<TResponse = unknown, B = any>(
  path: string,
  body?: B,
): Promise<TResponse> {
  return request<TResponse, B>(path, { method: "POST", body });
}

export function apiPut<TResponse = unknown, B = any>(
  path: string,
  body?: B,
): Promise<TResponse> {
  return request<TResponse, B>(path, { method: "PUT", body });
}

export function apiDelete<TResponse = unknown, B = any>(
  path: string,
  body?: B,
): Promise<TResponse> {
  return request<TResponse, B>(path, { method: "DELETE", body });
}

/* ------------------------------------------------------------------
   Objekt-API (für Aufrufe wie api.get / api.post)
-------------------------------------------------------------------*/

export const api = {
  get: apiGet,
  post: apiPost,
  put: apiPut,
  delete: apiDelete,
};
