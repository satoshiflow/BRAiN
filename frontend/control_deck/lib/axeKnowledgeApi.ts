// Axe Knowledge API Client
// Client-side API functions for the Axe Knowledge Document System

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://127.0.0.1:8000";

// ============================================================================
// Types
// ============================================================================

export type DocumentCategory =
  | "general"
  | "technical"
  | "business"
  | "process"
  | "reference"
  | "custom";

export type KnowledgeDocument = {
  id: string;
  title: string;
  content: string;
  category: DocumentCategory;
  tags: string[];
  source?: string | null;
  author?: string | null;
  importance: number;
  embedding_model?: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocumentCreate = {
  title: string;
  content: string;
  category: DocumentCategory;
  tags?: string[];
  source?: string;
  author?: string;
  importance?: number;
};

export type KnowledgeDocumentUpdate = Partial<KnowledgeDocumentCreate>;

export type KnowledgeDocumentsResponse = {
  items: KnowledgeDocument[];
  total: number;
};

export type CategoryStats = {
  category: DocumentCategory;
  count: number;
};

export type CategoryStatsResponse = {
  categories: CategoryStats[];
  total: number;
};

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch all knowledge documents with optional filtering
 */
export async function fetchKnowledgeDocuments(params?: {
  category?: DocumentCategory;
  search?: string;
  tag?: string;
  skip?: number;
  limit?: number;
}): Promise<KnowledgeDocumentsResponse> {
  const searchParams = new URLSearchParams();
  
  if (params?.category) searchParams.append("category", params.category);
  if (params?.search) searchParams.append("search", params.search);
  if (params?.tag) searchParams.append("tag", params.tag);
  if (params?.skip !== undefined) searchParams.append("skip", String(params.skip));
  if (params?.limit !== undefined) searchParams.append("limit", String(params.limit));
  
  const query = searchParams.toString();
  const url = `${API_BASE}/api/axe/knowledge${query ? `?${query}` : ""}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch knowledge documents: ${res.status}`);
  return res.json();
}

/**
 * Fetch a single knowledge document by ID
 */
export async function fetchKnowledgeDocument(id: string): Promise<KnowledgeDocument> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch knowledge document: ${res.status}`);
  return res.json();
}

/**
 * Fetch top documents by importance
 */
export async function fetchTopDocuments(limit?: number): Promise<KnowledgeDocument[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.append("limit", String(limit));
  
  const query = params.toString();
  const url = `${API_BASE}/api/axe/knowledge/top${query ? `?${query}` : ""}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch top documents: ${res.status}`);
  return res.json();
}

/**
 * Fetch category statistics
 */
export async function fetchCategoryStats(): Promise<CategoryStatsResponse> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/stats`);
  if (!res.ok) throw new Error(`Failed to fetch category stats: ${res.status}`);
  return res.json();
}

/**
 * Create a new knowledge document
 */
export async function createKnowledgeDocument(
  data: KnowledgeDocumentCreate
): Promise<KnowledgeDocument> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to create knowledge document: ${err}`);
  }
  return res.json();
}

/**
 * Update an existing knowledge document
 */
export async function updateKnowledgeDocument(
  id: string,
  data: KnowledgeDocumentUpdate
): Promise<KnowledgeDocument> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to update knowledge document: ${err}`);
  }
  return res.json();
}

/**
 * Delete a knowledge document
 */
export async function deleteKnowledgeDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/axe/knowledge/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete knowledge document: ${res.status}`);
}

/**
 * Search knowledge documents by query
 */
export async function searchKnowledgeDocuments(
  query: string,
  params?: {
    category?: DocumentCategory;
    limit?: number;
  }
): Promise<KnowledgeDocument[]> {
  const searchParams = new URLSearchParams();
  searchParams.append("q", query);
  
  if (params?.category) searchParams.append("category", params.category);
  if (params?.limit !== undefined) searchParams.append("limit", String(params.limit));
  
  const queryString = searchParams.toString();
  const url = `${API_BASE}/api/axe/knowledge/search?${queryString}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to search knowledge documents: ${res.status}`);
  return res.json();
}
