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
