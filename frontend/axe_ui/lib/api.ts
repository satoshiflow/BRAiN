import { getApiBase } from "@/lib/config";
import type {
  ApiHealthResponse,
  AxeAttachmentUploadResponse,
  AxeChatRequest,
  AxeChatResponse,
} from "@/lib/contracts";

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const apiBase = getApiBase();
  const response = await fetch(`${apiBase}${path}`, {
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
    throw new Error(`API error ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchJson<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function postAxeChat(
  payload: AxeChatRequest,
  customHeaders?: Record<string, string>,
): Promise<AxeChatResponse> {
  return apiRequest<AxeChatResponse>("/api/axe/chat", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}

export async function getApiHealth(): Promise<ApiHealthResponse> {
  return apiRequest<ApiHealthResponse>("/api/health");
}

export async function uploadAxeAttachment(
  file: File,
  customHeaders?: Record<string, string>
): Promise<AxeAttachmentUploadResponse> {
  const apiBase = getApiBase();
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${apiBase}/api/axe/upload`, {
    method: "POST",
    body,
    headers: {
      Accept: "application/json",
      ...(customHeaders || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Upload error ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<AxeAttachmentUploadResponse>;
}
