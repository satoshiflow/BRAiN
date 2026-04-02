import { fetchJson, postJson } from "./client";

export type PaperclipTargetType = "company" | "project" | "issue" | "agent" | "execution";
export type PaperclipPermission = "view" | "request_escalation" | "request_approval" | "request_retry";
export type PaperclipAction = "request_escalation" | "request_approval" | "request_retry";

export interface PaperclipHandoffRequest {
  target_type: PaperclipTargetType;
  target_ref: string;
  skill_run_id?: string;
  mission_id?: string;
  decision_id?: string;
  correlation_id?: string;
  permissions: PaperclipPermission[];
}

export interface PaperclipHandoffResponse {
  handoff_url: string;
  expires_at: string;
  jti: string;
  target_type: PaperclipTargetType;
  target_ref: string;
}

export interface PaperclipActionRequestItem {
  request_id: string;
  tenant_id?: string | null;
  principal_id: string;
  action: PaperclipAction;
  reason: string;
  status: "pending" | "approved" | "rejected";
  target_type: "execution";
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

export interface PaperclipActionRequestListResponse {
  items: PaperclipActionRequestItem[];
  total: number;
}

export const externalAppsApi = {
  createPaperclipHandoff: (payload: PaperclipHandoffRequest) =>
    postJson<PaperclipHandoffResponse, PaperclipHandoffRequest>("/api/external-apps/paperclip/handoff", payload),
  listPaperclipActionRequests: () =>
    fetchJson<PaperclipActionRequestListResponse>("/api/external-apps/paperclip/action-requests"),
  approvePaperclipActionRequest: (requestId: string, reason: string) =>
    postJson<PaperclipActionRequestItem, { reason: string }>(
      `/api/external-apps/paperclip/action-requests/${requestId}/approve`,
      { reason }
    ),
  rejectPaperclipActionRequest: (requestId: string, reason: string) =>
    postJson<PaperclipActionRequestItem, { reason: string }>(
      `/api/external-apps/paperclip/action-requests/${requestId}/reject`,
      { reason }
    ),
};
