const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_URL ?? "http://localhost:8000";

export type UIModuleRoute = {
  path: string;
  label: string;
  icon?: string;
};

export type UIModuleManifest = {
  name: string;
  label: string;
  category?: string | null;
  version?: string | null;
  routes: UIModuleRoute[];
};

export type DNAMetadata = {
  reason?: string | null;
  source: string;
  parent_snapshot_id?: number | null;
};

export type AgentDNASnapshot = {
  id: number;
  agent_id: string;
  version: number;
  dna: Record<string, unknown>;
  traits: Record<string, unknown>;
  karma_score?: number | null;
  created_at: string;
  meta: DNAMetadata;
};

export type DNAHistoryResponse = {
  agent_id: string;
  snapshots: AgentDNASnapshot[];
};

export type ImmuneEvent = {
  id: number;
  agent_id?: string | null;
  module?: string | null;
  severity: "INFO" | "WARNING" | "CRITICAL";
  type: "POLICY_VIOLATION" | "ERROR_SPIKE" | "SELF_HEALING_ACTION";
  message: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type ImmuneHealthSummary = {
  active_issues: number;
  critical_issues: number;
  last_events: ImmuneEvent[];
};

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    const short = text.length > 200 ? text.slice(0, 200) + "…" : text;
    throw new Error(`Request failed: ${res.status} ${res.statusText} – ${short}`);
  }
  return (await res.json()) as T;
}

export async function fetchModuleManifests(): Promise<UIModuleManifest[]> {
  const res = await fetch(`${API_BASE}/api/core/modules/ui-manifest`);
  return handleJson<UIModuleManifest[]>(res);
}

export async function fetchDNAHistory(
  agentId: string,
): Promise<DNAHistoryResponse> {
  const res = await fetch(
    `${API_BASE}/api/dna/agents/${encodeURIComponent(agentId)}/history`,
  );
  return handleJson<DNAHistoryResponse>(res);
}

export async function fetchImmuneHealth(): Promise<ImmuneHealthSummary> {
  const res = await fetch(`${API_BASE}/api/immune/health`);
  return handleJson<ImmuneHealthSummary>(res);
}
