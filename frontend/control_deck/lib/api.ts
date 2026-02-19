/**
 * API Client for BRAiN Backend
 *
 * Security features:
 * - Request timeout (prevents hanging requests)
 * - SSRF protection (URL whitelist)
 * - Automatic 401 handling (redirects to login)
 * - Error sanitization (no internal details leaked)
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://localhost:8000";

// SSRF Protection: Whitelist of allowed hosts
const ALLOWED_HOSTS = [
  "localhost",
  "127.0.0.1",
  "brain-api.falklabs.de",
  "api.brain.falklabs.de",
];

interface FetchJsonOptions extends RequestInit {
  timeout?: number;
}

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public response?: any
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Validate URL against SSRF attack patterns
 */
function validateURL(urlString: string): URL {
  let url: URL;

  try {
    url = new URL(urlString);
  } catch {
    throw new Error("Invalid URL");
  }

  // SSRF Protection: Only allow whitelisted hosts
  if (!ALLOWED_HOSTS.includes(url.hostname)) {
    throw new Error(`Host not allowed: ${url.hostname}`);
  }

  // Prevent private IP ranges in production
  const hostname = url.hostname;
  if (process.env.NODE_ENV === "production") {
    if (
      hostname.startsWith("192.168.") ||
      hostname.startsWith("10.") ||
      hostname.startsWith("172.") ||
      hostname === "localhost" ||
      hostname === "127.0.0.1"
    ) {
      throw new Error("Private IP access denied in production");
    }
  }

  return url;
}

/**
 * Fetch JSON data with timeout and error handling
 */
export async function fetchJson<T>(
  path: string,
  options?: FetchJsonOptions
): Promise<T> {
  const timeout = options?.timeout || 30000; // 30s default
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  // Validate URL for SSRF protection
  validateURL(url);

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...options?.headers,
      },
    });

    clearTimeout(timeoutId);

    // Handle 401 Unauthorized - redirect to login
    if (res.status === 401) {
      if (typeof window !== "undefined") {
        const currentPath = window.location.pathname;
        window.location.href = `/auth/signin?callbackUrl=${encodeURIComponent(
          currentPath
        )}`;
      }
      throw new APIError(401, "Unauthorized");
    }

    // Handle other error responses
    if (!res.ok) {
      let errorMessage = `Request failed with status ${res.status}`;

      try {
        const errorData = await res.json();
        // Use error message from backend if available
        errorMessage =
          errorData.message || errorData.detail || errorMessage;
      } catch {
        // If response is not JSON, use text
        const text = await res.text().catch(() => "");
        if (text && process.env.NODE_ENV === "development") {
          errorMessage = text;
        }
      }

      throw new APIError(res.status, errorMessage);
    }

    return (await res.json()) as T;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof APIError) {
      throw error;
    }

    // Handle abort (timeout)
    if (error instanceof Error && error.name === "AbortError") {
      throw new APIError(
        408,
        "Request timeout - please try again"
      );
    }

    // Network errors
    if (error instanceof TypeError) {
      throw new APIError(
        0,
        "Network error - please check your connection"
      );
    }

    // Unknown errors - don't expose details in production
    if (process.env.NODE_ENV === "production") {
      throw new APIError(500, "An unexpected error occurred");
    }

    throw error;
  }
}

/**
 * Helper for GET requests
 */
export function getJSON<T>(path: string, options?: FetchJsonOptions): Promise<T> {
  return fetchJson<T>(path, { ...options, method: "GET" });
}

/**
 * Helper for POST requests
 */
export function postJSON<T>(
  path: string,
  data: unknown,
  options?: FetchJsonOptions
): Promise<T> {
  return fetchJson<T>(path, {
    ...options,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    body: JSON.stringify(data),
  });
}

/**
 * Helper for PUT requests
 */
export function putJSON<T>(
  path: string,
  data: unknown,
  options?: FetchJsonOptions
): Promise<T> {
  return fetchJson<T>(path, {
    ...options,
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    body: JSON.stringify(data),
  });
}

/**
 * Helper for DELETE requests
 */
export function deleteJSON<T>(
  path: string,
  options?: FetchJsonOptions
): Promise<T> {
  return fetchJson<T>(path, { ...options, method: "DELETE" });
}
