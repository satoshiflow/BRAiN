import { postJson } from "./client";

export interface IntentCandidateSkill {
  skill_key: string;
  version: number;
  score: number;
  reason: string;
}

export interface IntentDraftSuggestion {
  suggested_skill_key: string;
  rationale: string;
  recommended_capabilities: string[];
}

export interface IntentExecuteRequest {
  intent_text?: string;
  source_url?: string;
  problem_statement?: string;
  context?: Record<string, unknown>;
  input_payload?: Record<string, unknown>;
  auto_execute?: boolean;
  min_confidence?: number;
  mission_id?: string;
}

export interface IntentExecuteResponse {
  resolution_type: "matched_skill" | "draft_required";
  normalized_intent: string;
  confidence: number;
  reason: string;
  matched_skill_key?: string | null;
  matched_skill_version?: number | null;
  candidates: IntentCandidateSkill[];
  draft_suggestion?: IntentDraftSuggestion | null;
  skill_run?: {
    id: string;
    state: string;
    skill_key: string;
    skill_version: number;
  } | null;
}

export const intentApi = {
  execute: (payload: IntentExecuteRequest) =>
    postJson<IntentExecuteResponse, IntentExecuteRequest>("/api/intent/execute", payload),
};
