import { fetchJson, postJson } from "./client";

export type DomainEscalationStatus = "queued" | "in_review" | "approved" | "denied" | "cancelled";

export interface DomainEscalationTriage {
  domain_area: string;
  executor_slug?: string | null;
  target_type?: string | null;
  target_ref?: string | null;
  recommended_queue: string;
  recommended_owner: string;
  routing_hint: string;
}

export interface DomainEscalationItem {
  escalation_id: string;
  status: DomainEscalationStatus;
  received_at: string;
  domain_key: string;
  requested_by: string;
  risk_tier: string;
  correlation_id?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  decision_reason?: string | null;
  notes: Record<string, unknown>;
  triage: DomainEscalationTriage;
}

export interface DomainEscalationListResponse {
  items: DomainEscalationItem[];
  total: number;
}

export interface DomainEscalationDecisionPayload {
  status: DomainEscalationStatus;
  decision_reason: string;
  notes?: Record<string, unknown>;
  triage_updates?: Record<string, string>;
}

export const supervisorApi = {
  listDomainEscalations: (limit = 50) =>
    fetchJson<DomainEscalationListResponse>(`/api/supervisor/escalations/domain?limit=${limit}`),
  getDomainEscalation: (escalationId: string) =>
    fetchJson<DomainEscalationItem>(`/api/supervisor/escalations/domain/${escalationId}`),
  decideDomainEscalation: (escalationId: string, payload: DomainEscalationDecisionPayload) =>
    postJson<DomainEscalationItem, DomainEscalationDecisionPayload>(
      `/api/supervisor/escalations/domain/${escalationId}/decision`,
      payload
    ),
};
