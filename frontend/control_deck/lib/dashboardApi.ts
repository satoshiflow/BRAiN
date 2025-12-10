const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_URL ?? "http://localhost:8000";

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

export async function fetchCoreHealth(): Promise<CoreHealth> {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  return handleJson<CoreHealth>(res);
}

export async function fetchMissionsHealth(): Promise<MissionsHealth> {
  const res = await fetch(`${API_BASE}/api/missions/health`, {
    cache: "no-store",
  });
  return handleJson<MissionsHealth>(res);
}

export async function fetchSupervisorHealth(): Promise<SupervisorHealth> {
  const res = await fetch(`${API_BASE}/api/supervisor/health`, {
    cache: "no-store",
  });
  return handleJson<SupervisorHealth>(res);
}

export async function fetchMissionsOverviewStats(): Promise<MissionsOverviewStats> {
  const res = await fetch(`${API_BASE}/api/missions/stats/overview`, {
    cache: "no-store",
  });
  return handleJson<MissionsOverviewStats>(res);
}

export async function fetchThreatsOverviewStats(): Promise<ThreatsOverviewStats> {
  const res = await fetch(`${API_BASE}/api/threats/stats/overview`, {
    cache: "no-store",
  });
  return handleJson<ThreatsOverviewStats>(res);
}

export async function fetchImmuneHealth(): Promise<ImmuneHealthSummary> {
  const res = await fetch(`${API_BASE}/api/immune/health`, {
    cache: "no-store",
  });
  return handleJson<ImmuneHealthSummary>(res);
}