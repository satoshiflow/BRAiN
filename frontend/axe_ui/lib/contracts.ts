export type AxeChatRole = "system" | "user" | "assistant";

export interface AxeChatMessage {
  role: AxeChatRole;
  content: string;
}

export interface AxeChatRequest {
  model: string;
  messages: AxeChatMessage[];
  temperature?: number;
  attachments?: string[];
  session_id?: string;
}

export interface AxeChatResponse {
  text: string;
  raw: Record<string, unknown>;
  run_id?: string;
  worker_run_id?: string;
  session_id?: string;
  message_id?: string;
}

export interface AxeContextTelemetry {
  estimated_prompt_tokens: number;
  max_allowed_prompt_tokens: number;
  context_mode: "full" | "compacted" | "retrieval_augmented";
  trim_applied: boolean;
  trim_reason?: string | null;
  token_class: "small" | "medium" | "large";
  compression_applied: boolean;
  retrieval_applied: boolean;
  selected_segment_counts: Record<string, number>;
}

export type AxeWorkerStatus = "queued" | "running" | "waiting_input" | "completed" | "failed";

export interface AxeWorkerArtifact {
  type: string;
  label: string;
  url?: string;
  content?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AxeWorkerUpdate {
  worker_run_id: string;
  session_id: string;
  message_id: string;
  worker_type: "auto" | "opencode" | "miniworker" | "openclaw";
  activity_source: "worker_run" | "skillrun_tasklease";
  status: AxeWorkerStatus;
  label: string;
  detail: string;
  updated_at: string;
  artifacts?: AxeWorkerArtifact[];
}

export interface TaskQueueTaskResponse {
  task_id: string;
  status:
    | "pending"
    | "scheduled"
    | "claimed"
    | "running"
    | "completed"
    | "failed"
    | "cancelled"
    | "timeout"
    | "retrying";
  error_message?: string | null;
  updated_at: string;
  payload?: Record<string, unknown>;
}

export interface ApiHealthResponse {
  status?: string;
  version?: string;
}

export interface AxeAttachmentUploadResponse {
  attachment_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  expires_at: string;
}

export type AxeProvider = "openai" | "groq" | "ollama" | "mock";
export type AxeSanitizationLevel = "none" | "moderate" | "strict";

export interface AxeProviderRuntimeResponse {
  provider: AxeProvider;
  base_url: string;
  api_key_configured: boolean;
  model: string;
  timeout_seconds: number;
  sanitization_level: AxeSanitizationLevel;
}

export interface AxeProviderRuntimeUpdateRequest {
  provider: AxeProvider;
  force_sanitization_level?: AxeSanitizationLevel;
}

export type AxeSessionStatus = "active" | "deleted";
export type AxeSessionMessageRole = "user" | "assistant";

export interface AxeSessionSummary {
  id: string;
  title: string;
  preview?: string | null;
  status: AxeSessionStatus;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_at?: string | null;
}

export interface AxeSessionMessage {
  id: string;
  session_id: string;
  role: AxeSessionMessageRole;
  content: string;
  attachments: string[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AxeSessionDetail extends AxeSessionSummary {
  messages: AxeSessionMessage[];
}

export interface AxeSessionCreateRequest {
  title?: string;
}

export interface AxeSessionUpdateRequest {
  title: string;
}

export interface AxeSessionAppendMessageRequest {
  role: AxeSessionMessageRole;
  content: string;
  attachments?: string[];
  metadata?: Record<string, unknown>;
}

export type AdminUserRole = "admin" | "operator" | "viewer";

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  role: AdminUserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string | null;
}

export interface AdminInvitation {
  id: string;
  email: string;
  role: AdminUserRole;
  token: string;
  expires_at: string;
  invitation_url: string;
}

export type DecisionOutcome = "accept" | "reject" | "modified_accept";

export interface PurposeEvaluationRecord {
  id: string;
  decision_context_id: string;
  purpose_profile_id: string;
  outcome: DecisionOutcome;
  requires_human_review: boolean;
  purpose_score: number;
  sovereignty_score: number;
  required_modifications: string[];
  reasons: string[];
  governance_snapshot: Record<string, unknown>;
  mission_id?: string | null;
  correlation_id?: string | null;
  created_by: string;
}

export interface PurposeEvaluationListResponse {
  items: PurposeEvaluationRecord[];
  total: number;
}

export interface RoutingDecisionRecord {
  id: string;
  decision_context_id: string;
  task_profile_id: string;
  purpose_evaluation_id?: string | null;
  worker_candidates: string[];
  filtered_candidates: string[];
  selected_worker?: string | null;
  selected_skill_or_plan?: string | null;
  strategy: string;
  reasoning: string;
  governance_snapshot: Record<string, unknown>;
  mission_id?: string | null;
  correlation_id?: string | null;
  created_by: string;
}

export interface RoutingDecisionListResponse {
  items: RoutingDecisionRecord[];
  total: number;
}

export interface ProviderPortalProviderRecord {
  id: string;
  display_name: string;
  slug: string;
  is_enabled: boolean;
  health_status: "healthy" | "degraded" | "failed" | "unknown";
  secret_configured?: boolean;
  key_hint_masked?: string | null;
  last_health_at?: string | null;
}

export interface ProviderPortalListResponse {
  items: ProviderPortalProviderRecord[];
  total: number;
}
