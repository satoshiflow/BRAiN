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
  event?: ImmuneEvent;
}

interface IncidentSignalPayload {
  id: string;
  type: string;
  source: string;
  severity: Severity;
  entity: string;
  context: Record<string, unknown>;
  correlation_id: string;
  blast_radius: number;
  confidence: number;
  recurrence: number;
}

interface EvaluateSignalResponse {
  signal: IncidentSignalPayload;
  decision: {
    decision_id: string;
    signal_id: string;
    action: string;
    priority_score: number;
    reason: string;
    requires_governance_hook: boolean;
    correlation_id?: string | null;
    created_at: string;
  };
}

interface BackendAuditEntry {
  audit_id: string;
  event_type: string;
  action: string;
  severity: Severity;
  resource_type: string;
  resource_id: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

interface BackendAuditResponse {
  items: BackendAuditEntry[];
}

interface BackendMetrics {
  total_signals: number;
  total_decisions: number;
  actions: Record<string, number>;
  by_source: Record<string, number>;
}

function mapAuditEntry(entry: BackendAuditEntry): ImmuneEvent {
  return {
    id: entry.audit_id,
    timestamp: entry.timestamp,
    severity: entry.severity,
    component: `${entry.resource_type}:${entry.resource_id}`,
    trigger: entry.event_type,
    action: entry.action,
    status: "resolved",
    details: entry.details,
  };
}

function severityForAction(action: ImmuneAction["action"], fallback: Severity): Severity {
  if (action === "escalate") {
    return "critical";
  }
  if (action === "retry") {
    return fallback === "critical" ? "critical" : "warning";
  }
  return "info";
}

function buildManualSignal(action: ImmuneAction): IncidentSignalPayload {
  const fallbackSeverity = action.event?.severity ?? "warning";
  const severity = severityForAction(action.action, fallbackSeverity);
  const now = Date.now();
  const random = Math.random().toString(36).slice(2, 8);

  return {
    id: `cd3-${action.action}-${now}-${random}`,
    type: `manual.${action.action}`,
    source: "controldeck-v3",
    severity,
    entity: action.event?.component || action.eventId,
    context: {
      requested_action: action.action,
      requested_from: "controldeck-v3",
      original_event_id: action.eventId,
      original_event: action.event || null,
    },
    correlation_id: action.eventId,
    blast_radius: severity === "critical" ? 3 : 1,
    confidence: 0.9,
    recurrence: action.action === "retry" ? 1 : 0,
  };
}

export const immuneApi = {
  getEvents: async (limit = 50, severity?: Severity) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (severity) params.append("severity", severity);

    const payload = await fetchJson<BackendAuditResponse>(`/api/immune-orchestrator/audit?${params}`);
    const mapped = payload.items.map(mapAuditEntry);
    return mapped.slice(0, limit);
  },

  getEvent: async (eventId: string) => {
    const payload = await fetchJson<BackendAuditResponse>("/api/immune-orchestrator/audit");
    const match = payload.items.find((entry) => entry.audit_id === eventId);
    if (!match) {
      throw new Error(`Immune event not found: ${eventId}`);
    }

    return mapAuditEntry(match);
  },

  getStats: async () => {
    const [metrics, audit] = await Promise.all([
      fetchJson<BackendMetrics>("/api/immune-orchestrator/metrics"),
      fetchJson<BackendAuditResponse>("/api/immune-orchestrator/audit"),
    ]);

    const severityCounts = audit.items.reduce(
      (acc, entry) => {
        acc[entry.severity] += 1;
        return acc;
      },
      { critical: 0, warning: 0, info: 0 }
    );

    const totalEvents = metrics.total_signals || audit.items.length;
    const resolvedActions = (metrics.actions.mitigate || 0) + (metrics.actions.warn || 0);
    const successRate = totalEvents > 0 ? Math.min(1, resolvedActions / totalEvents) : 1;

    return {
      totalEvents,
      criticalCount: severityCounts.critical,
      warningCount: severityCounts.warning,
      infoCount: severityCounts.info,
      successRate,
      avgRecoveryTime: 0,
      topTriggers: Object.entries(metrics.by_source || {})
        .map(([trigger, count]) => ({ trigger, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5),
    } as ImmuneStats;
  },

  triggerAction: async (action: ImmuneAction) => {
    const signal = buildManualSignal(action);
    return postJson<EvaluateSignalResponse, IncidentSignalPayload>(
      "/api/immune-orchestrator/signals",
      signal
    );
  },

  subscribe: () => createEventSource("/api/immune-orchestrator/stream"),

  mapAuditEntry,
};
