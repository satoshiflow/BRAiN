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

export interface CognitiveAssociationCase {
  source_type: string;
  source_id: string;
  title: string;
  score: number;
  summary: string;
  metadata: Record<string, unknown>;
}

export interface CognitiveAssessment {
  assessment_id: string;
  tenant_id?: string | null;
  mission_id?: string | null;
  result: {
    result_version: string;
    confidence: number;
    risk: string[];
    impact: number;
    novelty: number;
    governance_flags: string[];
    routing_hint?: string | null;
  };
  perception: {
    normalized_intent: string;
    intent_keywords: string[];
    intent_modes: string[];
    risk_hints: string[];
    impact_hints: string[];
    novelty_hints: string[];
  };
  association: {
    memory_cases: CognitiveAssociationCase[];
    knowledge_cases: CognitiveAssociationCase[];
    total_cases: number;
  };
  evaluation: {
    confidence: number;
    novelty_score: number;
    impact_score: number;
    governance_hints: string[];
    risk_hints: string[];
  };
  recommended_skill_candidates: IntentCandidateSkill[];
  created_at: string;
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
  cognitive_assessment?: CognitiveAssessment | null;
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
