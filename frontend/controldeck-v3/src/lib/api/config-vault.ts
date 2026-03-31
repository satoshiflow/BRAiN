import { fetchJson, postJson } from "./client";

export type ConfigClassification = "secret" | "sensitive" | "public_config";
export type ConfigValueType = "string" | "integer" | "boolean" | "url" | "json" | "pem";

export interface VaultDefinition {
  key: string;
  label: string;
  description: string;
  classification: ConfigClassification;
  value_type: ConfigValueType;
  editable: boolean;
  generator_supported: boolean;
  rotation_supported: boolean;
  validation: Record<string, unknown>;
}

export interface VaultValue {
  key: string;
  classification: ConfigClassification;
  value_type: ConfigValueType;
  effective_source: "db_override" | "environment" | "default";
  is_set: boolean;
  masked_value: unknown;
  updated_at?: string | null;
  updated_by?: string | null;
}

interface VaultDefinitionsResponse {
  items: VaultDefinition[];
  total: number;
}

interface VaultValuesResponse {
  items: VaultValue[];
  total: number;
}

interface VaultValidateResponse {
  valid: boolean;
  errors: string[];
}

interface VaultGenerateResponse {
  key: string;
  generated: boolean;
  masked_value: unknown;
  revealed_value?: string | null;
}

export interface VaultRotationRequest {
  key: string;
  status: "pending" | "approved" | "rejected";
  classification: ConfigClassification;
  requested_by: string;
  requested_at: string;
  requested_reason?: string | null;
  masked_candidate: unknown;
}

interface VaultRotationListResponse {
  items: VaultRotationRequest[];
  total: number;
}

export const configVaultApi = {
  listDefinitions: () => fetchJson<VaultDefinitionsResponse>("/api/config/vault/definitions"),
  listValues: (classification?: ConfigClassification) => {
    const suffix = classification ? `?classification=${classification}` : "";
    return fetchJson<VaultValuesResponse>(`/api/config/vault/values${suffix}`);
  },
  validateValue: (key: string, value: unknown) =>
    postJson<VaultValidateResponse, { value: unknown }>(`/api/config/vault/validate/${key}`, { value }),
  updateValue: (key: string, value: unknown, reason?: string) =>
    postJson<VaultValue, { value: unknown; reason?: string }>(`/api/config/vault/values/${key}`, {
      value,
      reason,
    }),
  generateValue: (key: string, length?: number, reason?: string) =>
    postJson<VaultGenerateResponse, { length?: number; reason?: string }>(`/api/config/vault/generate/${key}`, {
      length,
      reason,
    }),
  requestRotation: (key: string, payload: { value?: unknown; generate?: boolean; length?: number; reason?: string }) =>
    postJson<VaultRotationRequest, { value?: unknown; generate?: boolean; length?: number; reason?: string }>(
      `/api/config/vault/rotate/${key}/request`,
      payload
    ),
  listPendingRotations: () => fetchJson<VaultRotationListResponse>("/api/config/vault/rotate/pending"),
  approveRotation: (key: string, reason?: string) =>
    postJson<VaultValue, { reason?: string }>(`/api/config/vault/rotate/${key}/approve`, { reason }),
  rejectRotation: (key: string, reason?: string) =>
    postJson<VaultRotationRequest, { reason?: string }>(`/api/config/vault/rotate/${key}/reject`, { reason }),
};
