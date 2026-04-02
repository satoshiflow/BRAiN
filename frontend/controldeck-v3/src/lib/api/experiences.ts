import { postJson } from "./client";

export type ExperienceIntent = "explain" | "present" | "sell" | "summarize";
export type ExperienceType = "landingpage" | "customer_explainer" | "mobile_view" | "chat_answer" | "presentation";
export type AudienceType = "customer" | "partner" | "internal" | "public";
export type OutputType = "answer" | "ui" | "presentation" | "action" | "artifact" | "event";
export type OutputTarget = "chat" | "web" | "mobile" | "admin" | "system";

export interface InputEnvelope {
  type: "text" | "voice" | "image" | "file" | "url" | "event" | "api";
  source: "user" | "system" | "agent";
  content: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  context?: Record<string, unknown>;
}

export interface ExperienceRenderRequest {
  intent: ExperienceIntent;
  experience_type: ExperienceType;
  subject: {
    type: string;
    id?: string | null;
    query?: string | null;
  };
  audience?: {
    type: AudienceType;
    id?: string | null;
  };
  context?: {
    device?: string;
    locale?: string;
    customer_id?: string | null;
    region?: string | null;
    season?: string | null;
    user_skill?: string | null;
  };
  input?: InputEnvelope | null;
}

export interface ExperienceSection {
  component: string;
  data_ref: string;
  title?: string | null;
  props?: Record<string, unknown>;
}

export interface ExperienceSourceRef {
  id: string;
  title: string;
  type: string;
  tags: string[];
}

export interface ExperiencePayload {
  schema_version: string;
  experience_type: ExperienceType;
  variant: string;
  context: Record<string, unknown>;
  data: Record<string, unknown>;
  sources: ExperienceSourceRef[];
  sections: ExperienceSection[];
  safety: {
    mode: string;
    warnings: string[];
  };
  cache: {
    ttl_seconds: number;
    persist: boolean;
  };
}

export interface OutputEnvelope {
  schema_version: string;
  type: OutputType;
  target: OutputTarget;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface ExperienceRenderResponse {
  output: OutputEnvelope;
}

export const experiencesApi = {
  render: (payload: ExperienceRenderRequest) =>
    postJson<ExperienceRenderResponse, ExperienceRenderRequest>("/api/experiences/render", payload),
};
