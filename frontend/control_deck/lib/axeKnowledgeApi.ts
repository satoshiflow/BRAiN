const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://127.0.0.1:8000";

export type DocumentCategory =
  | "system"
  | "domain"
  | "procedure"
  | "faq"
  | "reference"
  | "custom";

export type KnowledgeDocument = {
  id: string;
  name: string;
  description: string | null;
  category: DocumentCategory;
  content: string;
  content_type: string;
  metadata: Record<string, unknown>;
  tags: string[];
  is_enabled: boolean;
  access_count: number;
  importance_score: number;
  version: number;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
};

export type KnowledgeDocumentCreate = {
  name: string;
  description?: string;
  category: DocumentCategory;
  content: string;
  content_type?: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
  importance_score?: number;
};

export type KnowledgeDocumentUpdate = Partial<KnowledgeDocumentCreate> & {
  is_enabled?: boolean;
};

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as T;
}

export async function fetchKnowledgeDocuments(params?: {
  category?: DocumentCategory;
  enabled_only?: boolean;
  limit?: number;
  offset?: number;
  tags?: string[];
  search_query?: string;
}): Promise<KnowledgeDocument[]> {
  const searchParams = new URLSearchParams();

  if (params?.category) searchParams.set("category", params.category);
  if (params?.enabled_only !== undefined) {
    searchParams.set("enabled_only", String(params.enabled_only));
  }
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.search_query) searchParams.set("search_query", params.search_query);

  const url = `${API_BASE}/api/axe/knowledge?${searchParams}`;
  const res = await fetch(url);
  return handleResponse<KnowledgeDocument[]>(res);
}

export async function fetchKnowledgeDocument(id: string): Promise<KnowledgeDocument> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/${id}`);
  return handleResponse<KnowledgeDocument>(res);
}

export async function fetchTopDocuments(limit: number = 5): Promise<KnowledgeDocument[]> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/top?limit=${limit}`);
  return handleResponse<KnowledgeDocument[]>(res);
}

export async function fetchCategoryStats(): Promise<Record<string, number>> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/stats`);
  return handleResponse<Record<string, number>>(res);
}

export async function createKnowledgeDocument(
  data: KnowledgeDocumentCreate
): Promise<KnowledgeDocument> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<KnowledgeDocument>(res);
}

export async function updateKnowledgeDocument(
  id: string,
  data: KnowledgeDocumentUpdate
): Promise<KnowledgeDocument> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<KnowledgeDocument>(res);
}

export async function deleteKnowledgeDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Delete failed: ${text}`);
  }
}
