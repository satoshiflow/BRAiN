import { getApiBase } from "@/lib/config";
import type {
  ApiHealthResponse,
  AxeAttachmentUploadResponse,
  AxeChatRequest,
  AxeChatResponse,
  AxeWorkerUpdate,
  AxeSessionAppendMessageRequest,
  AxeSessionDetail,
  AxeSessionMessage,
  AxeSessionCreateRequest,
  AxeSessionSummary,
  AxeSessionUpdateRequest,
  AxeProviderRuntimeResponse,
  AxeProviderRuntimeUpdateRequest,
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

export async function getAxeWorkerRun(
  workerRunId: string,
  customHeaders?: Record<string, string>
): Promise<AxeWorkerUpdate> {
  return apiRequest<AxeWorkerUpdate>(`/api/axe/workers/${workerRunId}`, {
    method: "GET",
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

export async function getAxeProviderRuntime(
  customHeaders?: Record<string, string>
): Promise<AxeProviderRuntimeResponse> {
  return apiRequest<AxeProviderRuntimeResponse>("/api/axe/provider/runtime", {
    method: "GET",
    headers: customHeaders,
  });
}

export async function updateAxeProviderRuntime(
  payload: AxeProviderRuntimeUpdateRequest,
  customHeaders?: Record<string, string>
): Promise<AxeProviderRuntimeResponse> {
  return apiRequest<AxeProviderRuntimeResponse>("/api/axe/provider/runtime", {
    method: "PUT",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}

export async function listAxeSessions(
  customHeaders?: Record<string, string>
): Promise<AxeSessionSummary[]> {
  return apiRequest<AxeSessionSummary[]>("/api/axe/sessions", {
    method: "GET",
    headers: customHeaders,
  });
}

export async function createAxeSession(
  payload: AxeSessionCreateRequest,
  customHeaders?: Record<string, string>
): Promise<AxeSessionSummary> {
  return apiRequest<AxeSessionSummary>("/api/axe/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}

export async function getAxeSession(
  sessionId: string,
  customHeaders?: Record<string, string>
): Promise<AxeSessionDetail> {
  return apiRequest<AxeSessionDetail>(`/api/axe/sessions/${sessionId}`, {
    method: "GET",
    headers: customHeaders,
  });
}

export async function updateAxeSession(
  sessionId: string,
  payload: AxeSessionUpdateRequest,
  customHeaders?: Record<string, string>
): Promise<AxeSessionSummary> {
  return apiRequest<AxeSessionSummary>(`/api/axe/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}

export async function deleteAxeSession(
  sessionId: string,
  customHeaders?: Record<string, string>
): Promise<void> {
  const apiBase = getApiBase();
  const response = await fetch(`${apiBase}/api/axe/sessions/${sessionId}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(customHeaders || {}),
    },
    cache: "no-store",
  });

  if (!response.ok && response.status !== 204) {
    const text = await response.text();
    throw new Error(`API error ${response.status}: ${text || response.statusText}`);
  }
}

export async function appendAxeSessionMessage(
  sessionId: string,
  payload: AxeSessionAppendMessageRequest,
  customHeaders?: Record<string, string>
): Promise<AxeSessionMessage> {
  return apiRequest<AxeSessionMessage>(`/api/axe/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}
