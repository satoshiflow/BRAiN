// src/lib/brainApi.ts
// Zentrale API-Schicht für das BRAiN Control Deck
// Mapped direkt auf das FastAPI-Backend unter http://localhost:8000

export type Json = Record<string, any>;

const API_BASE =
  (process.env.NEXT_PUBLIC_BRAIN_API_BASE_URL ??
    process.env.NEXT_PUBLIC_BRAIN_API_BASE ??
    "http://localhost:8000")
    .replace(/\/+$/, "");

// ---------- Basis-Helper ----------

async function apiGet<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GET ${path} → HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
}

async function apiPost<T>(path: string, body: Json): Promise<T> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body ?? {}),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`POST ${path} → HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
}

async function apiPut<T>(path: string, body: Json): Promise<T> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body ?? {}),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`PUT ${path} → HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
}

async function apiDelete(path: string): Promise<void> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`DELETE ${path} → HTTP ${resp.status}: ${text}`);
  }
}

// ---------- Typen ----------

export interface BackendHealth {
  status: string;
  message?: string;
  version?: string;
}

export interface MissionsInfo {
  name: string;
  version: string;
  description?: string;
  queue?: string;
}

export interface MissionsHealth {
  status: string;
}

export interface MissionEnqueuePayload {
  type: string;
  payload: Json;
}

export interface MissionEnqueueResponse {
  mission_id: string;
  status: string;
}

export interface MissionQueueEntry {
  id: string;
  type: string;
  status: string;
  created_at?: string;
}

export interface ConnectorsInfo {
  name: string;
  version: string;
}

export interface ConnectorsList {
  connectors: Json[];
}

export interface AgentsInfo {
  name: string;
  version: string;
  status: string;
  description?: string;
  default_model?: string;
}

export interface AxeInfo {
  name: string;
  version: string;
  status: string;
  description?: string;
  gateway?: string;
}

export interface AxeMessageRequest {
  message: string;
  metadata?: Json;
}

export interface AxeMessageResponse {
  ok: boolean;
  message: string;
  raw?: Json;
}

export interface LlmDebugRequest {
  prompt?: string;
}

export interface LlmDebugResponse {
  ok: boolean;
  model: string;
  prompt: string;
  raw_response: Json;
}

// ---------- Öffentliche API ----------

export const brainApi = {
  // Basis / Health
  health: () => apiGet<BackendHealth>("/api/health"),

  // Missions
  missions: {
    info: () => apiGet<MissionsInfo>("/api/missions/info"),
    health: () => apiGet<MissionsHealth>("/api/missions/health"),
    enqueue: (payload: MissionEnqueuePayload) =>
      apiPost<MissionEnqueueResponse>("/api/missions/enqueue", payload),
    queuePreview: () =>
      apiGet<MissionQueueEntry[]>("/api/missions/queue"),
    agentsInfo: () => apiGet<Json>("/api/missions/agents/info"),
  },

  // Connectors
  connectors: {
    info: () => apiGet<ConnectorsInfo>("/api/connectors/info"),
    list: () => apiGet<ConnectorsList>("/api/connectors/list"),
  },

  // Agents
  agents: {
    info: () => apiGet<AgentsInfo>("/api/agents/info"),
    chat: (body: { message: string; agent_id?: string; metadata?: Json }) =>
      apiPost<Json>("/api/agents/chat", body),
  },

  // AXE
  axe: {
    info: () => apiGet<AxeInfo>("/api/axe/info"),
    sendMessage: (payload: AxeMessageRequest) =>
      apiPost<AxeMessageResponse>("/api/axe/message", payload),
  },

  // LLM-Debug
  debug: {
    llmPing: (body: LlmDebugRequest) =>
      apiPost<LlmDebugResponse>("/api/debug/llm-ping", body),
  },

  // Sovereign Mode
  sovereignMode: {
    info: () => apiGet<import("@/types/sovereign").SovereignInfo>("/api/sovereign-mode/info"),
    status: () => apiGet<import("@/types/sovereign").SovereignMode>("/api/sovereign-mode/status"),
    changeMode: (payload: import("@/types/sovereign").ModeChangeRequest) =>
      apiPost<import("@/types/sovereign").SovereignMode>("/api/sovereign-mode/mode", payload),

    // Bundles
    listBundles: (status?: import("@/types/sovereign").BundleStatus) =>
      apiGet<import("@/types/sovereign").Bundle[]>(
        `/api/sovereign-mode/bundles${status ? `?status=${status}` : ""}`
      ),
    getBundle: (bundleId: string) =>
      apiGet<import("@/types/sovereign").Bundle>(`/api/sovereign-mode/bundles/${bundleId}`),
    loadBundle: (payload: import("@/types/sovereign").BundleLoadRequest) =>
      apiPost<import("@/types/sovereign").Bundle>("/api/sovereign-mode/bundles/load", payload),
    validateBundle: (bundleId: string, force?: boolean) =>
      apiPost<import("@/types/sovereign").ValidationResult>(
        `/api/sovereign-mode/bundles/${bundleId}/validate${force ? "?force=true" : ""}`,
        {}
      ),
    discoverBundles: () =>
      apiPost<import("@/types/sovereign").BundleDiscoveryResult>(
        "/api/sovereign-mode/bundles/discover",
        {}
      ),
    removeQuarantine: (bundleId: string) =>
      apiDelete(`/api/sovereign-mode/bundles/${bundleId}/quarantine`),

    // Network
    checkNetwork: () =>
      apiGet<import("@/types/sovereign").NetworkCheckResult>("/api/sovereign-mode/network/check"),

    // Configuration
    getConfig: () => apiGet<import("@/types/sovereign").ModeConfig>("/api/sovereign-mode/config"),
    updateConfig: (updates: Partial<import("@/types/sovereign").ModeConfig>) =>
      apiPut<import("@/types/sovereign").ModeConfig>("/api/sovereign-mode/config", updates),

    // Audit
    getAuditLog: (limit?: number, eventType?: string) =>
      apiGet<import("@/types/sovereign").AuditEntry[]>(
        `/api/sovereign-mode/audit?${limit ? `limit=${limit}` : "limit=100"}${
          eventType ? `&event_type=${eventType}` : ""
        }`
      ),

    // Statistics
    getStatistics: () =>
      apiGet<import("@/types/sovereign").SovereignStatistics>("/api/sovereign-mode/statistics"),
  },
};

export default brainApi;
