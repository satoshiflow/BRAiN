import { fetchJson, postJson } from "./client";

export type RuntimeOverrideLevel =
  | "emergency_override"
  | "governor_override"
  | "manual_approved_override"
  | "policy_decision"
  | "feature_flags"
  | "registry_config"
  | "hard_defaults";

export interface RuntimeControlInfo {
  name: string;
  resolver_path: string;
  override_priority: RuntimeOverrideLevel[];
  notes: string[];
}

export interface RuntimeDecisionContext {
  tenant_id?: string | null;
  environment?: string;
  mission_type?: string;
  skill_type?: string | null;
  agent_role?: string | null;
  risk_score?: number;
  budget_state?: Record<string, unknown>;
  system_health?: Record<string, unknown>;
  feature_context?: Record<string, unknown>;
}

export interface AppliedPolicy {
  policy_id: string;
  reason: string;
  effect: string;
}

export interface AppliedOverride {
  level: RuntimeOverrideLevel;
  key: string;
  value: unknown;
  reason: string;
}

export interface ExplainTraceStep {
  level: RuntimeOverrideLevel;
  summary: string;
  changes: Record<string, unknown>;
}

export interface ResolverResponse {
  decision_id: string;
  effective_config: Record<string, unknown>;
  selected_model: string;
  selected_worker: string;
  selected_route: string;
  applied_policies: AppliedPolicy[];
  applied_overrides: AppliedOverride[];
  explain_trace: ExplainTraceStep[];
  validation: {
    valid: boolean;
    issues: string[];
  };
}

export type OverrideRequestStatus = "pending" | "approved" | "rejected";

export interface RuntimeOverrideRequestItem {
  request_id: string;
  tenant_id?: string | null;
  tenant_scope: "tenant" | "system";
  key: string;
  value: unknown;
  reason: string;
  status: OverrideRequestStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  decision_reason?: string | null;
  expires_at?: string | null;
}

export interface RuntimeOverrideRequestListResponse {
  items: RuntimeOverrideRequestItem[];
  total: number;
}

export interface RuntimeActiveOverride {
  request_id: string;
  key: string;
  value: unknown;
  reason: string;
  tenant_id?: string | null;
  expires_at?: string | null;
}

export interface RuntimeActiveOverrideListResponse {
  items: RuntimeActiveOverride[];
  total: number;
}

export type RegistryVersionStatus = "draft" | "promoted" | "superseded";

export interface RuntimeRegistryVersionItem {
  version_id: string;
  scope: "tenant" | "system";
  tenant_id?: string | null;
  status: RegistryVersionStatus;
  config_patch: Record<string, unknown>;
  reason: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  promoted_by?: string | null;
  promoted_at?: string | null;
  promotion_reason?: string | null;
}

export interface RuntimeRegistryVersionListResponse {
  items: RuntimeRegistryVersionItem[];
  total: number;
}

export interface RuntimeControlTimelineEvent {
  event_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor_id?: string | null;
  actor_type?: string | null;
  tenant_id?: string | null;
  correlation_id?: string | null;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface RuntimeControlTimelineResponse {
  items: RuntimeControlTimelineEvent[];
  total: number;
}

export interface ExternalOpsAlertItem {
  alert_id: string;
  severity: string;
  category: string;
  title: string;
  summary: string;
  app_slug?: string | null;
  request_id?: string | null;
  escalation_id?: string | null;
  target_ref?: string | null;
  skill_run_id?: string | null;
  task_id?: string | null;
  age_seconds: number;
}

export interface ExternalOpsSloMetrics {
  pending_action_requests: number;
  stale_action_requests: number;
  stale_supervisor_escalations: number;
  handoff_failures_24h: number;
  retry_approvals_24h: number;
  avg_action_request_age_seconds: number;
}

export interface ExternalOpsObservabilityResponse {
  generated_at: string;
  metrics: ExternalOpsSloMetrics;
  alerts: ExternalOpsAlertItem[];
}

export interface RuntimeOverrideRequestCreate {
  key: string;
  value: unknown;
  reason: string;
  tenant_scope?: "tenant" | "system";
  expires_at?: string;
}

export const runtimeControlApi = {
  getInfo: () => fetchJson<RuntimeControlInfo>("/api/runtime-control/info"),
  resolve: (context: RuntimeDecisionContext) =>
    postJson<ResolverResponse, { context: RuntimeDecisionContext }>("/api/runtime-control/resolve", { context }),
  listRequests: () => fetchJson<RuntimeOverrideRequestListResponse>("/api/runtime-control/overrides/requests"),
  listActiveOverrides: () => fetchJson<RuntimeActiveOverrideListResponse>("/api/runtime-control/overrides/active"),
  createRequest: (payload: RuntimeOverrideRequestCreate) =>
    postJson<RuntimeOverrideRequestItem, RuntimeOverrideRequestCreate>("/api/runtime-control/overrides/requests", payload),
  approveRequest: (requestId: string, reason: string) =>
    postJson<RuntimeOverrideRequestItem, { reason: string }>(
      `/api/runtime-control/overrides/requests/${requestId}/approve`,
      { reason }
    ),
  rejectRequest: (requestId: string, reason: string) =>
    postJson<RuntimeOverrideRequestItem, { reason: string }>(
      `/api/runtime-control/overrides/requests/${requestId}/reject`,
      { reason }
    ),
  listRegistryVersions: () => fetchJson<RuntimeRegistryVersionListResponse>("/api/runtime-control/registry/versions"),
  createRegistryVersion: (payload: {
    scope: "tenant" | "system";
    config_patch: Record<string, unknown>;
    reason: string;
  }) => postJson<RuntimeRegistryVersionItem, typeof payload>("/api/runtime-control/registry/versions", payload),
  promoteRegistryVersion: (versionId: string, reason: string) =>
    postJson<RuntimeRegistryVersionItem, { reason: string }>(
      `/api/runtime-control/registry/versions/${versionId}/promote`,
      { reason }
    ),
  listTimeline: (limit = 100) =>
    fetchJson<RuntimeControlTimelineResponse>(`/api/runtime-control/timeline?limit=${limit}`),
  getExternalOpsObservability: () =>
    fetchJson<ExternalOpsObservabilityResponse>("/api/runtime-control/external-ops/observability"),
};
