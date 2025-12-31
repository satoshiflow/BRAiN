/**
 * NeuroRail API Client (Phase 3 Frontend)
 *
 * Type-safe API client for NeuroRail backend endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://localhost:8000';

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || error.detail?.error || response.statusText);
  }

  return response.json();
}

// ============================================================================
// Identity API
// ============================================================================

export interface TraceChain {
  mission?: {
    mission_id: string;
    created_at: string;
    parent_mission_id?: string;
    tags?: Record<string, string>;
  };
  plan?: {
    plan_id: string;
    mission_id: string;
    plan_type: string;
    created_at: string;
  };
  job?: {
    job_id: string;
    plan_id: string;
    job_type: string;
    created_at: string;
  };
  attempt?: {
    attempt_id: string;
    job_id: string;
    attempt_number: number;
    created_at: string;
  };
}

export const identityAPI = {
  async getTraceChain(entityType: string, entityId: string): Promise<TraceChain> {
    return fetchAPI(`/api/neurorail/v1/identity/trace/${entityType}/${entityId}`);
  },

  async createMission(payload: { parent_mission_id?: string; tags?: Record<string, string> }) {
    return fetchAPI('/api/neurorail/v1/identity/mission', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

// ============================================================================
// Lifecycle API
// ============================================================================

export interface LifecycleState {
  entity_type: string;
  entity_id: string;
  state: string;
  last_updated: string;
}

export interface StateTransition {
  transition_id: string;
  entity_type: string;
  entity_id: string;
  from_state: string | null;
  to_state: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export const lifecycleAPI = {
  async getState(entityType: string, entityId: string): Promise<LifecycleState> {
    return fetchAPI(`/api/neurorail/v1/lifecycle/state/${entityType}/${entityId}`);
  },

  async getHistory(entityType: string, entityId: string): Promise<StateTransition[]> {
    return fetchAPI(`/api/neurorail/v1/lifecycle/history/${entityType}/${entityId}`);
  },
};

// ============================================================================
// Audit API
// ============================================================================

export interface AuditEvent {
  audit_id: string;
  timestamp: string;
  mission_id?: string;
  plan_id?: string;
  job_id?: string;
  attempt_id?: string;
  event_type: string;
  event_category: string;
  severity: string;
  message: string;
  details?: Record<string, any>;
}

export interface AuditStats {
  total_events: number;
  events_by_severity: Record<string, number>;
  events_by_category: Record<string, number>;
  recent_errors: number;
}

export const auditAPI = {
  async getEvents(params: {
    mission_id?: string;
    attempt_id?: string;
    severity?: string;
    limit?: number;
  }): Promise<AuditEvent[]> {
    const queryParams = new URLSearchParams();
    if (params.mission_id) queryParams.append('mission_id', params.mission_id);
    if (params.attempt_id) queryParams.append('attempt_id', params.attempt_id);
    if (params.severity) queryParams.append('severity', params.severity);
    if (params.limit) queryParams.append('limit', params.limit.toString());

    return fetchAPI(`/api/neurorail/v1/audit/events?${queryParams}`);
  },

  async getStats(): Promise<AuditStats> {
    return fetchAPI('/api/neurorail/v1/audit/stats');
  },
};

// ============================================================================
// Telemetry API
// ============================================================================

export interface TelemetrySnapshot {
  snapshot_id: string;
  timestamp: string;
  entity_counts: {
    missions: number;
    plans: number;
    jobs: number;
    attempts: number;
  };
  active_executions?: {
    running_attempts: number;
    queued_jobs: number;
  };
  error_rates?: {
    mechanical_errors: number;
    ethical_errors: number;
  };
  prometheus_metrics?: Record<string, number>;
}

export const telemetryAPI = {
  async getSnapshot(): Promise<TelemetrySnapshot> {
    return fetchAPI('/api/neurorail/v1/telemetry/snapshot');
  },

  async getMetrics(entityId: string): Promise<any> {
    return fetchAPI(`/api/neurorail/v1/telemetry/metrics/${entityId}`);
  },
};

// ============================================================================
// RBAC API
// ============================================================================

export interface RBACInfo {
  name: string;
  version: string;
  roles: Array<{
    role: string;
    permissions: string[];
  }>;
  permissions: string[];
  stats: {
    authorization_count: number;
    denied_count: number;
    denial_rate: number;
  };
}

export const rbacAPI = {
  async getInfo(): Promise<RBACInfo> {
    return fetchAPI('/api/neurorail/v1/rbac/info');
  },

  async checkPermission(payload: {
    user_id: string;
    role: string;
    permissions: string[];
    require_all?: boolean;
  }) {
    return fetchAPI('/api/neurorail/v1/rbac/check', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

// ============================================================================
// Stream API
// ============================================================================

export interface StreamStats {
  total_events_published: number;
  total_subscribers: number;
  subscribers_by_channel: Record<string, number>;
  buffer_sizes: Record<string, number>;
}

export const streamAPI = {
  async getStats(): Promise<StreamStats> {
    return fetchAPI('/api/neurorail/v1/stream/stats');
  },

  async publishEvent(payload: {
    channel: string;
    event_type: string;
    data: Record<string, any>;
  }) {
    return fetchAPI('/api/neurorail/v1/stream/publish', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async clearBuffers() {
    return fetchAPI('/api/neurorail/v1/stream/buffers', {
      method: 'DELETE',
    });
  },
};

// ============================================================================
// Export combined API
// ============================================================================

export const neurorailAPI = {
  identity: identityAPI,
  lifecycle: lifecycleAPI,
  audit: auditAPI,
  telemetry: telemetryAPI,
  rbac: rbacAPI,
  stream: streamAPI,
};
