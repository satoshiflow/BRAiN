const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://127.0.0.1:8000";

export type CoreHealth = {
  status?: string;
  env?: string;
  version?: string;
  timestamp?: string;
};

export type MissionsHealth = {
  status?: string;
  total?: number;
  running?: number;
  pending?: number;
  completed?: number;
  failed?: number;
};

export type SupervisorHealth = {
  status?: string;
  running?: number;
  completed?: number;
  failed?: number;
  cancelled?: number;
};

export type MissionsOverviewStats = {
  total?: number;
  running?: number;
  pending?: number;
  completed?: number;
  failed?: number;
};

export type ThreatsOverviewStats = {
  total?: number;
  critical?: number;
  warning?: number;
  info?: number;
};

export type ImmuneHealthSummary = {
  active_issues: number;
  critical_issues: number;
  last_events: {
    id: number;
    agent_id?: string | null;
    module?: string | null;
    severity: string;
    type: string;
    message: string;
    meta: Record<string, unknown>;
    created_at: string;
  }[];
};

export type Agent = {
  id: string;
  name: string;
  type: string;
  status: string;
};

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    const short = text.length > 200 ? text.slice(0, 200) + "…" : text;
    throw new Error(
      `Request failed: ${res.status} ${res.statusText} – ${short}`,
    );
  }
  return (await res.json()) as T;
}

// Verfügbarer Endpoint: GET /api/health
export async function fetchCoreHealth(): Promise<CoreHealth> {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  const data = await handleJson<{ status: string; version?: string }>(res);
  return {
    status: data.status === "healthy" ? "ok" : data.status,
    version: data.version,
    env: "production",
    timestamp: new Date().toISOString(),
  };
}

// Berechnet aus /api/missions
export async function fetchMissionsHealth(): Promise<MissionsHealth> {
  const res = await fetch(`${API_BASE}/api/missions`, { cache: "no-store" });
  const missions = await handleJson<Array<{ status?: string; progress?: number }>>(res);
  
  const total = missions.length;
  const running = missions.filter(m => m.status === "running" || (m.progress && m.progress > 0 && m.progress < 100)).length;
  const pending = missions.filter(m => m.status === "pending").length;
  const completed = missions.filter(m => m.status === "completed" || m.progress === 100).length;
  const failed = missions.filter(m => m.status === "failed").length;
  
  return {
    status: failed > 0 ? "degraded" : running > 0 ? "ok" : "ok",
    total,
    running,
    pending,
    completed,
    failed,
  };
}

// Fallback: Berechnet aus Agents-Daten
export async function fetchSupervisorHealth(): Promise<SupervisorHealth> {
  try {
    const res = await fetch(`${API_BASE}/api/agents`, { cache: "no-store" });
    const agents = await handleJson<Agent[]>(res);
    const running = agents.filter(a => a.status === "running").length;
    const idle = agents.filter(a => a.status === "idle").length;
    
    return {
      status: running > 0 ? "ok" : "idle",
      running,
      completed: idle,
      failed: 0,
      cancelled: 0,
    };
  } catch {
    // Fallback wenn /api/agents nicht verfügbar
    return {
      status: "unknown",
      running: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    };
  }
}

// Berechnet aus /api/missions
export async function fetchMissionsOverviewStats(): Promise<MissionsOverviewStats> {
  const res = await fetch(`${API_BASE}/api/missions`, { cache: "no-store" });
  const missions = await handleJson<Array<{ status?: string; progress?: number }>>(res);
  
  const total = missions.length;
  const running = missions.filter(m => m.status === "running" || (m.progress && m.progress > 0 && m.progress < 100)).length;
  const pending = missions.filter(m => m.status === "pending").length;
  const completed = missions.filter(m => m.status === "completed" || m.progress === 100).length;
  const failed = missions.filter(m => m.status === "failed").length;
  
  return { total, running, pending, completed, failed };
}

// Fallback: Keine Threats-Daten verfügbar
export async function fetchThreatsOverviewStats(): Promise<ThreatsOverviewStats> {
  return {
    total: 0,
    critical: 0,
    warning: 0,
    info: 0,
  };
}

// Fallback: Keine Immune-Daten verfügbar
export async function fetchImmuneHealth(): Promise<ImmuneHealthSummary> {
  return {
    active_issues: 0,
    critical_issues: 0,
    last_events: [],
  };
}
