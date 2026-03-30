import { fetchJson, postJson } from "./client";

export interface Skill {
  key: string;
  name: string;
  description: string;
  category: string;
  version: number;
  parameters: SkillParameter[];
  isEnabled: boolean;
}

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
  list: () =>
    fetchJson<SkillDefinitionListResponse>("/api/skill-definitions").then((res) =>
      res.items.map(mapSkill)
    ),

  getRuns: (limit = 50, state?: SkillRunState) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (state) {
      params.append("state", state);
    }
    return fetchJson<SkillRunListResponse>(`/api/skill-runs?${params}`).then((res) =>
      res.items.map(mapRun)
    );
  },

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
