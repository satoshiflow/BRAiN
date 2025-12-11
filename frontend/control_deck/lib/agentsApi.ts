const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_URL ?? "http://localhost:8000";

export type AgentKind = "system" | "user";

export type AgentSummary = {
  id: string;
  kind: AgentKind;
  label: string;
  description?: string | null;
};

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    const short = text.length > 200 ? text.slice(0, 200) + "…" : text;
    throw new Error(`Request failed: ${res.status} ${res.statusText} – ${short}`);
  }
  return (await res.json()) as T;
}

export async function fetchAgents(kind?: AgentKind): Promise<AgentSummary[]> {
  const url = new URL(`${API_BASE}/api/agents`);
  if (kind) url.searchParams.set("kind", kind);
  const res = await fetch(url.toString());
  return handleJson<AgentSummary[]>(res);
}

export async function fetchAgent(agentId: string): Promise<AgentSummary> {
  const res = await fetch(`${API_BASE}/api/agents/${encodeURIComponent(agentId)}`);
  return handleJson<AgentSummary>(res);
}