import { fetchJson, postJson } from "./client";

export type ExternalAppSlug = "paperclip" | "openclaw";
export type ExternalAppTargetType = "company" | "project" | "issue" | "agent" | "execution";
export type ExternalAppPermission = "view" | "request_escalation" | "request_approval" | "request_retry";
export type ExternalAppAction = "request_escalation" | "request_approval" | "request_retry";

export interface ExternalAppHandoffRequest {
  target_type: ExternalAppTargetType;
  target_ref: string;
  skill_run_id?: string;
  mission_id?: string;
  decision_id?: string;
  correlation_id?: string;
  permissions: ExternalAppPermission[];
}

export interface ExternalAppHandoffResponse {
  app_slug: ExternalAppSlug;
  handoff_url: string;
  expires_at: string;
  jti: string;
  target_type: ExternalAppTargetType;
  target_ref: string;
}

export interface ExternalAppActionRequestItem {
  request_id: string;
  app_slug: ExternalAppSlug;
  tenant_id?: string | null;
  principal_id: string;
  action: ExternalAppAction;
  reason: string;
  status: "pending" | "approved" | "rejected";
  target_type: ExternalAppTargetType;
  target_ref: string;
  skill_run_id?: string | null;
  mission_id?: string | null;
  decision_id?: string | null;
  correlation_id?: string | null;
  created_at: string;
  updated_at: string;
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  decision_reason?: string | null;
  execution_result: Record<string, string>;
}

export interface ExternalAppActionRequestListResponse {
  items: ExternalAppActionRequestItem[];
  total: number;
}

function basePath(appSlug: ExternalAppSlug): string {
  return `/api/external-apps/${appSlug}`;
}

export const externalAppsApi = {
  createHandoff: (appSlug: ExternalAppSlug, payload: ExternalAppHandoffRequest) =>
    postJson<ExternalAppHandoffResponse, ExternalAppHandoffRequest>(`${basePath(appSlug)}/handoff`, payload),
  listActionRequests: (appSlug: ExternalAppSlug) =>
    fetchJson<ExternalAppActionRequestListResponse>(`${basePath(appSlug)}/action-requests`),
  approveActionRequest: (appSlug: ExternalAppSlug, requestId: string, reason: string) =>
    postJson<ExternalAppActionRequestItem, { reason: string }>(`${basePath(appSlug)}/action-requests/${requestId}/approve`, { reason }),
  rejectActionRequest: (appSlug: ExternalAppSlug, requestId: string, reason: string) =>
    postJson<ExternalAppActionRequestItem, { reason: string }>(`${basePath(appSlug)}/action-requests/${requestId}/reject`, { reason }),
};
