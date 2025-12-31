/**
 * NeuroRail API Client
 * Type-safe wrapper for NeuroRail Phase 1 (Observe-only) endpoints
 */

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_URL ?? "http://localhost:8000";

// ============================================================================
// Type Definitions
// ============================================================================

// --- Identity Module ---

export type MissionIdentity = {
  mission_id: string;
  created_at: string;
  parent_mission_id: string | null;
  tags: Record<string, string>;
};

export type PlanIdentity = {
  plan_id: string;
  mission_id: string;
  created_at: string;
  plan_type: string;
  tags: Record<string, string>;
};

export type JobIdentity = {
  job_id: string;
  plan_id: string;
  created_at: string;
  job_type: string;
  tags: Record<string, string>;
};

export type AttemptIdentity = {
  attempt_id: string;
  job_id: string;
  created_at: string;
  attempt_number: number;
  retry_reason: string | null;
};

export type ResourceIdentity = {
  resource_uuid: string;
  attempt_id: string;
  created_at: string;
  resource_type: string;
  metadata: Record<string, any>;
};

export type TraceChain = {
  mission: MissionIdentity | null;
  plan: PlanIdentity | null;
  job: JobIdentity | null;
  attempt: AttemptIdentity | null;
  resources: ResourceIdentity[];
};

// --- Lifecycle Module ---

export type MissionState =
  | "pending"
  | "planning"
  | "planned"
  | "executing"
  | "completed"
  | "failed"
  | "timeout"
  | "cancelled";

export type JobState =
  | "pending"
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "timeout"
  | "cancelled";

export type AttemptState =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "timeout"
  | "orphan_killed";

export type StateTransitionEvent = {
  transition_id: string;
  timestamp: string;
  entity_type: "mission" | "job" | "attempt";
  entity_id: string;
  from_state: string | null;
  to_state: string;
  transition_type: string | null;
  metadata: Record<string, any>;
};

export type CurrentState = {
  entity_type: string;
  entity_id: string;
  current_state: string;
  last_transition_at: string | null;
};

// --- Audit Module ---

export type AuditEvent = {
  audit_id: string;
  timestamp: string;
  mission_id: string | null;
  plan_id: string | null;
  job_id: string | null;
  attempt_id: string | null;
  event_type: string;
  event_category: string;
  severity: "debug" | "info" | "warning" | "error" | "critical";
  message: string;
  details: Record<string, any> | null;
};

export type AuditEventsResponse = {
  events: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditStats = {
  total_events: number;
  events_by_severity: Record<string, number>;
  events_by_category: Record<string, number>;
  recent_errors: number;
};

// --- Telemetry Module ---

export type ExecutionMetrics = {
  attempt_id: string;
  entity_type: string;
  success: boolean;
  duration_ms: number | null;
  error_type: string | null;
  error_category: string | null;
  timestamp: string;
};

export type RealtimeSnapshot = {
  timestamp: string;
  entity_counts: {
    missions: number;
    plans: number;
    jobs: number;
    attempts: number;
  };
  active_executions: {
    running_attempts: number;
    queued_jobs: number;
  };
  error_rates: {
    mechanical_errors: number;
    ethical_errors: number;
  };
  prometheus_metrics: Record<string, any>;
};

// --- Governor Module ---

export type GovernorMode = "direct" | "rail";

export type ModeDecision = {
  mode: GovernorMode;
  reason: string;
  matched_rules: string[];
  decision_id: string;
  timestamp: string;
  logged_to_db: boolean;
};

export type GovernorStats = {
  total_decisions: number;
  direct_mode_count: number;
  rail_mode_count: number;
  recent_decisions: ModeDecision[];
};

// --- Error Codes ---

export type NeuroRailErrorCode =
  | "NR-E001" // Execution timeout
  | "NR-E002" // Budget exceeded
  | "NR-E003" // Retry exhausted
  | "NR-E004" // Upstream unavailable
  | "NR-E005" // Bad response format
  | "NR-E006" // Policy reflex cooldown
  | "NR-E007"; // Orphan killed

export type ErrorCategory = "mechanical" | "ethical" | "system";

export type NeuroRailError = {
  code: NeuroRailErrorCode;
  category: ErrorCategory;
  retriable: boolean;
  message: string;
  details?: Record<string, any>;
};

// ============================================================================
// Helper Functions
// ============================================================================

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    let errorData: any = {};
    try {
      errorData = JSON.parse(text);
    } catch {
      errorData = { detail: text };
    }

    // Check if it's a NeuroRail error code
    if (errorData.code && errorData.code.startsWith("NR-E")) {
      const nrError: NeuroRailError = {
        code: errorData.code as NeuroRailErrorCode,
        category: errorData.category || "system",
        retriable: errorData.retriable || false,
        message: errorData.message || errorData.detail || "Unknown error",
        details: errorData.details,
      };
      throw nrError;
    }

    // Generic error
    const short = text.length > 300 ? text.slice(0, 300) + "…" : text;
    throw new Error(
      `NeuroRail API error ${res.status}: ${res.statusText} – ${short}`
    );
  }
  return (await res.json()) as T;
}

function buildQueryString(params: Record<string, any>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

// ============================================================================
// Identity Module API
// ============================================================================

export async function createMissionIdentity(payload: {
  parent_mission_id?: string | null;
  tags?: Record<string, string>;
}): Promise<MissionIdentity> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/identity/mission`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<MissionIdentity>(res);
}

export async function createPlanIdentity(payload: {
  mission_id: string;
  plan_type?: string;
  tags?: Record<string, string>;
}): Promise<PlanIdentity> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/identity/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<PlanIdentity>(res);
}

export async function createJobIdentity(payload: {
  plan_id: string;
  job_type: string;
  tags?: Record<string, string>;
}): Promise<JobIdentity> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/identity/job`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<JobIdentity>(res);
}

export async function createAttemptIdentity(payload: {
  job_id: string;
  attempt_number: number;
  retry_reason?: string | null;
}): Promise<AttemptIdentity> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/identity/attempt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<AttemptIdentity>(res);
}

export async function fetchTraceChain(
  entityType: "mission" | "plan" | "job" | "attempt",
  entityId: string
): Promise<TraceChain> {
  const res = await fetch(
    `${API_BASE}/api/neurorail/v1/identity/trace/${entityType}/${encodeURIComponent(entityId)}`,
    { cache: "no-store" }
  );
  return handleJson<TraceChain>(res);
}

// ============================================================================
// Lifecycle Module API
// ============================================================================

export async function transitionState(
  entityType: "mission" | "job" | "attempt",
  payload: {
    entity_id: string;
    transition: string;
    metadata?: Record<string, any>;
  }
): Promise<StateTransitionEvent> {
  const res = await fetch(
    `${API_BASE}/api/neurorail/v1/lifecycle/transition/${entityType}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  return handleJson<StateTransitionEvent>(res);
}

export async function fetchCurrentState(
  entityType: "mission" | "job" | "attempt",
  entityId: string
): Promise<CurrentState> {
  const res = await fetch(
    `${API_BASE}/api/neurorail/v1/lifecycle/state/${entityType}/${encodeURIComponent(entityId)}`,
    { cache: "no-store" }
  );
  return handleJson<CurrentState>(res);
}

export async function fetchTransitionHistory(
  entityType: "mission" | "job" | "attempt",
  entityId: string,
  limit: number = 50
): Promise<StateTransitionEvent[]> {
  const qs = buildQueryString({ limit });
  const res = await fetch(
    `${API_BASE}/api/neurorail/v1/lifecycle/history/${entityType}/${encodeURIComponent(entityId)}${qs}`,
    { cache: "no-store" }
  );
  const data = await handleJson<{ transitions: StateTransitionEvent[] }>(res);
  return data.transitions || [];
}

// ============================================================================
// Audit Module API
// ============================================================================

export async function logAuditEvent(payload: {
  mission_id?: string | null;
  plan_id?: string | null;
  job_id?: string | null;
  attempt_id?: string | null;
  event_type: string;
  event_category: string;
  severity: "debug" | "info" | "warning" | "error" | "critical";
  message: string;
  details?: Record<string, any> | null;
}): Promise<AuditEvent> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/audit/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<AuditEvent>(res);
}

export async function fetchAuditEvents(params: {
  mission_id?: string;
  plan_id?: string;
  job_id?: string;
  attempt_id?: string;
  event_type?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditEventsResponse> {
  const qs = buildQueryString({
    mission_id: params.mission_id,
    plan_id: params.plan_id,
    job_id: params.job_id,
    attempt_id: params.attempt_id,
    event_type: params.event_type,
    severity: params.severity,
    limit: params.limit || 50,
    offset: params.offset || 0,
  });
  const res = await fetch(`${API_BASE}/api/neurorail/v1/audit/events${qs}`, {
    cache: "no-store",
  });
  return handleJson<AuditEventsResponse>(res);
}

export async function fetchAuditStats(): Promise<AuditStats> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/audit/stats`, {
    cache: "no-store",
  });
  return handleJson<AuditStats>(res);
}

// ============================================================================
// Telemetry Module API
// ============================================================================

export async function recordExecutionMetrics(
  payload: ExecutionMetrics
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/telemetry/record`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await handleJson<void>(res);
}

export async function fetchExecutionMetrics(
  entityId: string
): Promise<ExecutionMetrics> {
  const res = await fetch(
    `${API_BASE}/api/neurorail/v1/telemetry/metrics/${encodeURIComponent(entityId)}`,
    { cache: "no-store" }
  );
  return handleJson<ExecutionMetrics>(res);
}

export async function fetchTelemetrySnapshot(): Promise<RealtimeSnapshot> {
  const res = await fetch(`${API_BASE}/api/neurorail/v1/telemetry/snapshot`, {
    cache: "no-store",
  });
  return handleJson<RealtimeSnapshot>(res);
}

// ============================================================================
// Governor Module API
// ============================================================================

export async function decideModeExecution(payload: {
  job_type: string;
  context: Record<string, any>;
  shadow_evaluate?: boolean;
}): Promise<ModeDecision> {
  const res = await fetch(`${API_BASE}/api/governor/v1/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<ModeDecision>(res);
}

export async function fetchGovernorStats(): Promise<GovernorStats> {
  const res = await fetch(`${API_BASE}/api/governor/v1/stats`, {
    cache: "no-store",
  });
  return handleJson<GovernorStats>(res);
}

// ============================================================================
// Error Utilities
// ============================================================================

export function isNeuroRailError(error: any): error is NeuroRailError {
  return (
    error &&
    typeof error === "object" &&
    "code" in error &&
    typeof error.code === "string" &&
    error.code.startsWith("NR-E")
  );
}

export function formatErrorMessage(error: any): string {
  if (isNeuroRailError(error)) {
    return `[${error.code}] ${error.message}${error.retriable ? " (retriable)" : ""}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
