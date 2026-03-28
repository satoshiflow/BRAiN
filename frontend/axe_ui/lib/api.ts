import { getApiBase } from "@/lib/config";
import type {
  AdminInvitation,
  AdminUser,
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
  ProviderPortalListResponse,
  PurposeEvaluationListResponse,
  RoutingDecisionListResponse,
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

export async function listAdminUsers(customHeaders?: Record<string, string>): Promise<AdminUser[]> {
  return apiRequest<AdminUser[]>("/api/admin/users", {
    method: "GET",
    headers: customHeaders,
  });
}

export async function listAdminInvitations(customHeaders?: Record<string, string>): Promise<AdminInvitation[]> {
  return apiRequest<AdminInvitation[]>("/api/admin/invitations", {
    method: "GET",
    headers: customHeaders,
  });
}

export async function createAdminInvitation(
  payload: { email: string; role: "admin" | "operator" | "viewer" },
  customHeaders?: Record<string, string>
): Promise<AdminInvitation> {
  return apiRequest<AdminInvitation>("/api/auth/invitations", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}

export async function toggleAdminUserActive(
  userId: string,
  customHeaders?: Record<string, string>
): Promise<AdminUser> {
  return apiRequest<AdminUser>(`/api/admin/users/${userId}/deactivate`, {
    method: "POST",
    headers: customHeaders,
  });
}

export async function changeAdminUserRole(
  userId: string,
  role: "admin" | "operator" | "viewer",
  customHeaders?: Record<string, string>
): Promise<AdminUser> {
  return apiRequest<AdminUser>(`/api/admin/users/${userId}/role?new_role=${encodeURIComponent(role)}`, {
    method: "PUT",
    headers: customHeaders,
  });
}

export async function listPurposeEvaluations(
  limit = 5,
  customHeaders?: Record<string, string>
): Promise<PurposeEvaluationListResponse> {
  return apiRequest<PurposeEvaluationListResponse>(
    `/api/domain-agents/purpose-evaluations?limit=${limit}`,
    {
      method: "GET",
      headers: customHeaders,
    }
  );
}

export async function listRoutingDecisions(
  limit = 5,
  customHeaders?: Record<string, string>
): Promise<RoutingDecisionListResponse> {
  return apiRequest<RoutingDecisionListResponse>(
    `/api/domain-agents/routing-decisions?limit=${limit}`,
    {
      method: "GET",
      headers: customHeaders,
    }
  );
}

export async function listProviderPortalProviders(
  customHeaders?: Record<string, string>
): Promise<ProviderPortalListResponse> {
  return apiRequest<ProviderPortalListResponse>("/api/llm/providers", {
    method: "GET",
    headers: customHeaders,
  });
}

export interface AXERunCreate {
  skill_key: string;
  session_id?: string;
  input_payload: Record<string, unknown>;
  stream_tokens: boolean;
}

export interface AXERunResponse {
  id: string;
  skill_key: string;
  state: string;
  skill_run_id: string | null;
  session_id: string | null;
  output: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export async function createAXERun(
  payload: AXERunCreate,
  customHeaders?: Record<string, string>
): Promise<AXERunResponse> {
  return apiRequest<AXERunResponse>("/api/axe/runs", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: customHeaders,
  });
}

export async function getAXERun(
  runId: string,
  customHeaders?: Record<string, string>
): Promise<AXERunResponse> {
  return apiRequest<AXERunResponse>(`/api/axe/runs/${runId}`, {
    method: "GET",
    headers: customHeaders,
  });
}

export function createAXERunEventSource(runId: string): EventSource {
  const apiBase = getApiBase();
  const url = `${apiBase}/api/axe/runs/${runId}/events`;
  const eventSource = new EventSource(url, { withCredentials: true });
  eventSource.addEventListener("open", () => {});
  return eventSource;
}
