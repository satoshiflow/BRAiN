import { fetchJson, createEventSource, postJson } from "./client";

export type Severity = "critical" | "warning" | "info";

export type EventStatus = "pending" | "in_progress" | "resolved" | "failed" | "skipped";

export interface ImmuneEvent {
  id: string;
  timestamp: string;
  severity: Severity;
  component: string;
  trigger: string;
  action: string;
  status: EventStatus;
  result?: string;
  duration?: number;
  details?: Record<string, unknown>;
}

export interface ImmuneStats {
  totalEvents: number;
  criticalCount: number;
  warningCount: number;
  infoCount: number;
  successRate: number;
  avgRecoveryTime: number;
  topTriggers: { trigger: string; count: number }[];
}

export interface ImmuneAction {
  action: "retry" | "skip" | "escalate";
  eventId: string;
}

export const immuneApi = {
  getEvents: (limit = 50, severity?: Severity) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (severity) params.append("severity", severity);
    return fetchJson<ImmuneEvent[]>(`/api/immune-orchestrator/audit?${params}`);
  },

  getEvent: (eventId: string) =>
    fetchJson<ImmuneEvent>(`/api/immune-orchestrator/audit/${eventId}`),

  getStats: () => fetchJson<ImmuneStats>("/api/immune-orchestrator/decisions"),

  triggerAction: (action: ImmuneAction) =>
    postJson<{ success: boolean; message: string }, ImmuneAction>(
      "/api/immune-orchestrator/signals",
      action
    ),

  subscribe: () => createEventSource("/api/immune-orchestrator/stream"),
};
