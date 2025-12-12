export type AgentState = "healthy" | "degraded" | "offline" | "unknown";

export type SystemComponentStatus = {
  name: string;
  healthy: boolean;
  details?: Record<string, string>;
};

export type AgentStatus = {
  id: string;
  name: string;
  state: AgentState;
  last_heartbeat?: string | null;
  current_mission_id?: string | null;
  capabilities: string[];
  meta: Record<string, string>;
};

export type SupervisorStatus = {
  uptime_seconds: number;
  started_at: string;
  global_state: string;
  components: SystemComponentStatus[];
  total_agents: number;
  healthy_agents: number;
  degraded_agents: number;
  offline_agents: number;
  active_missions: number;
};

export type AgentControlAction = "pause" | "resume" | "kill" | "restart";

export type AgentControlRequest = {
  agent_id: string;
  action: AgentControlAction;
  reason?: string;
  requested_by?: string;
};

export type AgentControlResponse = {
  success: boolean;
  message: string;
  agent?: AgentStatus;
};

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    ...init,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Supervisor API error: ${res.status} ${res.statusText} - ${text}`,
    );
  }

  return res.json() as Promise<T>;
}

export async function fetchSupervisorStatus(): Promise<SupervisorStatus> {
  return request<SupervisorStatus>("/api/supervisor/status");
}

export async function fetchSupervisorAgents(): Promise<AgentStatus[]> {
  return request<AgentStatus[]>("/api/supervisor/agents");
}

export async function postSupervisorControl(
  payload: AgentControlRequest,
): Promise<AgentControlResponse> {
  return request<AgentControlResponse>("/api/supervisor/control", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
