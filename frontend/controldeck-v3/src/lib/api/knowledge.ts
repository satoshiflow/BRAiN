import { fetchJson, postJson, putJson } from "./client";

export interface KnowledgeItem {
  id: string;
  tenant_id: string | null;
  title: string;
  content: string;
  type: string;
  tags: string[];
  visibility: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeVersion {
  id: string;
  item_id: string;
  version: number;
  diff: Record<string, unknown>;
  created_at: string;
}

export interface KnowledgeListResponse {
  items: KnowledgeItem[];
  total: number;
}

export interface KnowledgeCreatePayload {
  title: string;
  content: string;
  type?: string;
  tags?: string[];
  visibility?: string;
  metadata?: Record<string, unknown>;
}

export interface KnowledgeIngestPayload {
  raw_text?: string;
  url?: string;
  code?: string;
  document_text?: string;
  title?: string;
  type?: string;
  tags?: string[];
  visibility?: string;
  metadata?: Record<string, unknown>;
}

export const knowledgeApi = {
  list: (query?: string, type?: string, tag?: string, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (query) params.append("query", query);
    if (type) params.append("type", type);
    if (tag) params.append("tag", tag);
    return fetchJson<KnowledgeListResponse>(`/api/knowledge-engine/items?${params}`);
  },

  search: (query: string, type?: string, limit = 20) => {
    const params = new URLSearchParams({ query, limit: String(limit) });
    if (type) params.append("type", type);
    return fetchJson<KnowledgeListResponse>(`/api/knowledge-engine/search?${params}`);
  },

  semanticSearch: (query: string, limit = 20) =>
    postJson<KnowledgeListResponse, { query: string; limit: number }>("/api/knowledge-engine/semantic-search", {
      query,
      limit,
    }),

  get: (itemId: string) => fetchJson<KnowledgeItem>(`/api/knowledge-engine/items/${itemId}`),

  create: (payload: KnowledgeCreatePayload) => postJson<KnowledgeItem, KnowledgeCreatePayload>("/api/knowledge-engine/items", payload),

  update: (itemId: string, payload: Partial<KnowledgeCreatePayload>) =>
    putJson<KnowledgeItem, Partial<KnowledgeCreatePayload>>(`/api/knowledge-engine/items/${itemId}`, payload),

  ingest: (payload: KnowledgeIngestPayload) =>
    postJson<{ item: KnowledgeItem; chunk_count: number }, KnowledgeIngestPayload>("/api/knowledge-engine/ingest", payload),

  related: (itemId: string) => fetchJson<{ item_id: string; related: KnowledgeItem[] }>(`/api/knowledge-engine/items/${itemId}/related`),

  versions: (itemId: string) => fetchJson<KnowledgeVersion[]>(`/api/knowledge-engine/items/${itemId}/versions`),

  listHelpDocs: (surface = "controldeck-v3", limit = 100) => {
    const params = new URLSearchParams({ surface, limit: String(limit) });
    return fetchJson<KnowledgeListResponse>(`/api/knowledge-engine/help?${params}`);
  },

  getHelpDoc: (helpKey: string, surface = "controldeck-v3") => {
    const params = new URLSearchParams({ surface });
    return fetchJson<KnowledgeItem>(`/api/knowledge-engine/help/${helpKey}?${params}`);
  },

  link: (sourceId: string, targetId: string, relationType: string) =>
    postJson<{ id: string }, { source_id: string; target_id: string; relation_type: string }>("/api/knowledge-engine/links", {
      source_id: sourceId,
      target_id: targetId,
      relation_type: relationType,
    }),
};
