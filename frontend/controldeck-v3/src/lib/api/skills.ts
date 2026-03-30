import { fetchJson, postJson, deleteRequest } from "./client";

export interface Skill {
  key: string;
  name: string;
  description: string;
  category: string;
  version: string;
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
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface SkillRun {
  id: string;
  skillKey: string;
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
  session_id?: string;
}

export const skillsApi = {
  list: () => fetchJson<Skill[]>("/api/skills"),

  get: (skillKey: string) => fetchJson<Skill>(`/api/skills/${skillKey}`),

  getRuns: (limit = 50, state?: SkillRunState) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (state) params.append("state", state);
    return fetchJson<SkillRun[]>(`/api/skill-runs?${params}`);
  },

  getRun: (runId: string) => fetchJson<SkillRun>(`/api/skill-runs/${runId}`),

  trigger: (trigger: SkillTrigger) =>
    postJson<{ id: string; state: string }, SkillTrigger>(
      "/api/skill-runs",
      trigger
    ),

  cancel: (runId: string) =>
    deleteRequest<void>(`/api/skill-runs/${runId}`),

  retry: (runId: string) =>
    postJson<{ id: string; state: string }, unknown>(`/api/skill-runs/${runId}/retry`, {}),
};
