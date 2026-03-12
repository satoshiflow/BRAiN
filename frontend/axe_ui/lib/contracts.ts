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
}

export interface AxeChatResponse {
  text: string;
  raw: Record<string, unknown>;
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

export type AxeProvider = "groq" | "ollama" | "mock";
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
