export type AxeChatRole = "system" | "user" | "assistant";

export interface AxeChatMessage {
  role: AxeChatRole;
  content: string;
}

export interface AxeChatRequest {
  model: string;
  messages: AxeChatMessage[];
  temperature?: number;
}

export interface AxeChatResponse {
  text: string;
  raw: Record<string, unknown>;
}

export interface ApiHealthResponse {
  status?: string;
  version?: string;
}
