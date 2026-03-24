import { fetchJson, getJSON, postJSON } from "@/lib/api";

export type ProviderType = "cloud" | "gateway" | "local";
export type AuthMode = "api_key" | "none";
export type ProviderHealth = "healthy" | "degraded" | "failed" | "unknown";

export interface ProviderAccount {
  id: string;
  slug: string;
  display_name: string;
  provider_type: ProviderType;
  base_url: string;
  auth_mode: AuthMode;
  is_enabled: boolean;
  is_local: boolean;
  supports_chat: boolean;
  supports_embeddings: boolean;
  supports_responses: boolean;
  notes?: string | null;
  secret_configured?: boolean;
  key_hint_masked?: string | null;
  health_status?: ProviderHealth;
  updated_at?: string;
}

export interface ProviderModel {
  id: string;
  provider_id: string;
  model_name: string;
  display_name: string;
  capabilities: Record<string, unknown>;
  is_enabled: boolean;
  priority: number;
  cost_class?: string | null;
  latency_class?: string | null;
  quality_class?: string | null;
  supports_tools: boolean;
  supports_json: boolean;
  supports_streaming: boolean;
}

export interface ProviderListResponse {
  items: ProviderAccount[];
  total: number;
}

export interface ProviderModelListResponse {
  items: ProviderModel[];
  total: number;
}

export async function listProviders(): Promise<ProviderListResponse> {
  return getJSON<ProviderListResponse>("/api/llm/providers");
}

export async function createProvider(payload: Partial<ProviderAccount>): Promise<ProviderAccount> {
  return postJSON<ProviderAccount>("/api/llm/providers", payload);
}

export async function patchProvider(
  providerId: string,
  payload: Partial<ProviderAccount>
): Promise<ProviderAccount> {
  return fetchJson<ProviderAccount>(`/api/llm/providers/${providerId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function setProviderSecret(
  providerId: string,
  secretValue: string
): Promise<{ provider_id: string; is_active: boolean; key_hint_masked: string; updated_at: string }> {
  return postJSON<{ provider_id: string; is_active: boolean; key_hint_masked: string; updated_at: string }>(
    `/api/llm/providers/${providerId}/secret`,
    { api_key: secretValue, activate: true }
  );
}

export async function deactivateProviderSecret(
  providerId: string
): Promise<{ provider_id: string; is_active: boolean; key_hint_masked: string; updated_at: string }> {
  return fetchJson<{ provider_id: string; is_active: boolean; key_hint_masked: string; updated_at: string }>(
    `/api/llm/providers/${providerId}/secret`,
    {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    }
  );
}

export async function testProvider(
  providerId: string,
  modelName?: string
): Promise<{
  provider_id: string;
  status: ProviderHealth;
  success: boolean;
  latency_ms?: number;
  error_code?: string;
  error_message?: string;
  checked_at: string;
  binding_projection: Record<string, unknown>;
}> {
  return postJSON<{
    provider_id: string;
    status: ProviderHealth;
    success: boolean;
    latency_ms?: number;
    error_code?: string;
    error_message?: string;
    checked_at: string;
    binding_projection: Record<string, unknown>;
  }>(
    `/api/llm/providers/${providerId}/test`,
    { model_name: modelName }
  );
}

export async function listProviderModels(providerId?: string): Promise<ProviderModelListResponse> {
  const suffix = providerId ? `?provider_id=${encodeURIComponent(providerId)}` : "";
  return getJSON<ProviderModelListResponse>(`/api/llm/models${suffix}`);
}

export async function createProviderModel(payload: Partial<ProviderModel>): Promise<ProviderModel> {
  return postJSON<ProviderModel>("/api/llm/models", payload);
}

export async function patchProviderModel(
  modelId: string,
  payload: Partial<ProviderModel>
): Promise<ProviderModel> {
  return fetchJson<ProviderModel>(`/api/llm/models/${modelId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
