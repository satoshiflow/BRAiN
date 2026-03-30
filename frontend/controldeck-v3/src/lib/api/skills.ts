import { fetchJson, postJson } from "./client";

export interface Skill {
  key: string;
  name: string;
  description: string;
  category: string;
  version: number;
  parameters: SkillParameter[];
  isEnabled: boolean;
  valueScore: number;
  effortSavedHours: number;
  qualityImpact: number;
  complexityLevel: string;
}

export type SkillSortBy = "skill_key" | "updated_at" | "value_score";

export interface SkillParameter {
  name: string;
  type: "string" | "number" | "boolean" | "object";
  required: boolean;
  description?: string;
  default?: unknown;
}

export type SkillRunState =
  | "queued"
  | "planning"
  | "waiting_approval"
  | "running"
  | "cancel_requested"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "timed_out";

export interface SkillRun {
  id: string;
  skillKey: string;
  skillVersion: number;
  state: SkillRunState;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface SkillRunEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface SkillTrigger {
  skill_key: string;
  input_payload: Record<string, unknown>;
  version?: number;
}

interface SkillDefinitionResponse {
  skill_key: string;
  version: number;
  status: string;
  purpose: string;
  required_capabilities: Array<{ capability_key: string }>;
  risk_tier: string;
  value_score: number;
  effort_saved_hours: number;
  quality_impact: number;
  complexity_level: string;
}

interface SkillDefinitionListResponse {
  items: SkillDefinitionResponse[];
  total: number;
}

interface SkillRunResponse {
  id: string;
  skill_key: string;
  skill_version: number;
  state: SkillRunState;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  failure_reason_sanitized?: string | null;
  created_at: string;
  state_changed_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

interface SkillRunListResponse {
  items: SkillRunResponse[];
  total: number;
}

interface SkillRunExecutionReport {
  skill_run: SkillRunResponse;
}

interface SkillValueScoreResponse {
  skill_key: string;
  version: number;
  value_score: number;
  source: string;
  effort_saved_hours: number;
  quality_impact: number;
  complexity_level: string;
  risk_tier: string;
  breakdown: Record<string, unknown>;
}

interface SkillValueHistoryItem {
  run_id: string;
  skill_version: number;
  state: string;
  created_at: string;
  overall_score?: number | null;
  value_score?: number | null;
  quality_impact?: number | null;
  effort_saved_hours?: number | null;
  source?: string | null;
}

interface SkillValueHistoryResponse {
  skill_key: string;
  items: SkillValueHistoryItem[];
  total: number;
}

export interface SkillLifecycleAnalyticsItem {
  skill_key: string;
  latest_version: number;
  value_score: number;
  success_rate: number;
  avg_overall_score: number;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  trend_delta: number;
  last_run_at?: string | null;
}

export interface SkillLifecycleAnalyticsResponse {
  summary: {
    total_skills: number;
    total_runs: number;
    avg_value_score: number;
    avg_success_rate: number;
    window_days: number;
  };
  items: SkillLifecycleAnalyticsItem[];
}

export interface SkillMarketplaceRankItem {
  rank: number;
  skill_key: string;
  latest_version: number;
  market_score: number;
  value_score: number;
  success_rate: number;
  avg_overall_score: number;
  run_volume_score: number;
  trend_delta: number;
  last_run_at?: string | null;
}

export interface SkillMarketplaceRankingResponse {
  window_days: number;
  generated_at: string;
  items: SkillMarketplaceRankItem[];
}

function mapSkill(def: SkillDefinitionResponse): Skill {
  return {
    key: def.skill_key,
    name: def.skill_key,
    description: def.purpose,
    category: def.risk_tier,
    version: def.version,
    parameters: def.required_capabilities.map((cap) => ({
      name: cap.capability_key,
      type: "object",
      required: true,
    })),
    isEnabled: def.status === "active" || def.status === "deprecated",
    valueScore: def.value_score || 0,
    effortSavedHours: def.effort_saved_hours || 0,
    qualityImpact: def.quality_impact || 0,
    complexityLevel: def.complexity_level || "medium",
  };
}

function mapRun(run: SkillRunResponse): SkillRun {
  return {
    id: run.id,
    skillKey: run.skill_key,
    skillVersion: run.skill_version,
    state: run.state,
    input: run.input_payload || {},
    output: run.output_payload || {},
    error: run.failure_reason_sanitized || undefined,
    createdAt: run.created_at,
    updatedAt: run.state_changed_at || run.created_at,
    startedAt: run.started_at || undefined,
    completedAt: run.finished_at || undefined,
  };
}

function buildIdempotencyKey(skillKey: string): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `${skillKey}-${Date.now()}-${random}`;
}

export const skillsApi = {
  list: (sortBy: SkillSortBy = "value_score", skillKey?: string) => {
    const params = new URLSearchParams({ sort_by: sortBy });
    if (skillKey) {
      params.set("skill_key", skillKey);
    }
    return fetchJson<SkillDefinitionListResponse>(`/api/skill-definitions?${params.toString()}`).then((res) =>
      res.items.map(mapSkill)
    );
  },

  getRuns: (limit = 50, state?: SkillRunState, skillKey?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (state) {
      params.append("state", state);
    }
    if (skillKey) {
      params.append("skill_key", skillKey);
    }
    return fetchJson<SkillRunListResponse>(`/api/skill-runs?${params}`).then((res) =>
      res.items.map(mapRun)
    );
  },

  getValueScore: (skillKey: string, version?: number) => {
    const params = new URLSearchParams();
    if (version) {
      params.set("version", String(version));
    }
    const suffix = params.toString();
    return fetchJson<SkillValueScoreResponse>(
      `/api/skill-definitions/${encodeURIComponent(skillKey)}/value-score${suffix ? `?${suffix}` : ""}`
    );
  },

  getValueHistory: (skillKey: string, limit = 30) =>
    fetchJson<SkillValueHistoryResponse>(
      `/api/skill-definitions/${encodeURIComponent(skillKey)}/value-history?limit=${limit}`
    ),

  getLifecycleAnalytics: (windowDays = 30, limit = 100) =>
    fetchJson<SkillLifecycleAnalyticsResponse>(
      `/api/economy/skills/lifecycle-analytics?window_days=${windowDays}&limit=${limit}`
    ),

  getMarketplaceRanking: (windowDays = 30, limit = 25) =>
    fetchJson<SkillMarketplaceRankingResponse>(
      `/api/economy/skills/marketplace-ranking?window_days=${windowDays}&limit=${limit}`
    ),

  getRun: (runId: string) => fetchJson<SkillRunResponse>(`/api/skill-runs/${runId}`).then(mapRun),

  trigger: async (trigger: SkillTrigger) => {
    const run = await postJson<SkillRunResponse, {
      skill_key: string;
      version?: number;
      input_payload: Record<string, unknown>;
      idempotency_key: string;
    }>("/api/skill-runs", {
      skill_key: trigger.skill_key,
      version: trigger.version,
      input_payload: trigger.input_payload,
      idempotency_key: buildIdempotencyKey(trigger.skill_key),
    });

    const report = await postJson<SkillRunExecutionReport, Record<string, never>>(
      `/api/skill-runs/${run.id}/execute`,
      {}
    );

    return mapRun(report.skill_run);
  },

  cancel: (runId: string) =>
    postJson<SkillRunResponse, Record<string, never>>(`/api/skill-runs/${runId}/cancel`, {}).then(mapRun),

  retry: async (runId: string) => {
    const original = await fetchJson<SkillRunResponse>(`/api/skill-runs/${runId}`);
    return skillsApi.trigger({
      skill_key: original.skill_key,
      version: original.skill_version,
      input_payload: original.input_payload || {},
    });
  },
};
