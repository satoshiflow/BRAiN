// Mission Templates API Client
// Client-side API functions for mission templates

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://127.0.0.1:8000";

// ============================================================================
// Types
// ============================================================================

export type TemplateStep = {
  order: number;
  action: string;
  config: Record<string, unknown>;
};

export type TemplateVariable = {
  type: "string" | "number" | "boolean" | "object" | "array";
  required: boolean;
  default?: unknown;
  description?: string;
};

export type MissionTemplate = {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  steps: TemplateStep[];
  variables: Record<string, TemplateVariable>;
  created_at?: string;
  updated_at?: string;
};

export type CreateTemplatePayload = {
  name: string;
  description?: string;
  category: string;
  steps: TemplateStep[];
  variables: Record<string, TemplateVariable>;
};

export type UpdateTemplatePayload = Partial<CreateTemplatePayload>;

export type InstantiateTemplatePayload = {
  variables: Record<string, unknown>;
  mission_name?: string;
};

export type InstantiateTemplateResponse = {
  mission_id: string;
  mission_name: string;
  status: string;
  template_id: string;
  variables_applied: Record<string, unknown>;
};

export type TemplateListResponse = {
  items: MissionTemplate[];
  total: number;
};

export type TemplateCategoriesResponse = {
  categories: string[];
};

// ============================================================================
// Helper Functions
// ============================================================================

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    const short = text.length > 200 ? text.slice(0, 200) + "…" : text;
    throw new Error(`Request failed: ${res.status} ${res.statusText} – ${short}`);
  }
  return (await res.json()) as T;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * List all mission templates with optional filtering
 */
export async function fetchTemplates(
  category?: string,
  search?: string
): Promise<TemplateListResponse> {
  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (search) params.append("search", search);
  
  const url = `${API_BASE}/api/missions/templates${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  return handleJson<TemplateListResponse>(res);
}

/**
 * Get all unique template categories
 */
export async function fetchTemplateCategories(): Promise<TemplateCategoriesResponse> {
  const res = await fetch(`${API_BASE}/api/missions/templates/categories`, {
    cache: "no-store",
  });
  return handleJson<TemplateCategoriesResponse>(res);
}

/**
 * Get a single template by ID
 */
export async function fetchTemplate(templateId: string): Promise<MissionTemplate> {
  const res = await fetch(
    `${API_BASE}/api/missions/templates/${encodeURIComponent(templateId)}`,
    { cache: "no-store" }
  );
  return handleJson<MissionTemplate>(res);
}

/**
 * Create a new mission template
 */
export async function createTemplate(
  payload: CreateTemplatePayload
): Promise<MissionTemplate> {
  const res = await fetch(`${API_BASE}/api/missions/templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<MissionTemplate>(res);
}

/**
 * Update an existing template
 */
export async function updateTemplate(
  templateId: string,
  payload: UpdateTemplatePayload
): Promise<MissionTemplate> {
  const res = await fetch(
    `${API_BASE}/api/missions/templates/${encodeURIComponent(templateId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  return handleJson<MissionTemplate>(res);
}

/**
 * Delete a template
 */
export async function deleteTemplate(templateId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/missions/templates/${encodeURIComponent(templateId)}`,
    {
      method: "DELETE",
    }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Delete failed: ${res.status} ${res.statusText} – ${text}`);
  }
}

/**
 * Instantiate a template into a mission
 */
export async function instantiateTemplate(
  templateId: string,
  payload: InstantiateTemplatePayload
): Promise<InstantiateTemplateResponse> {
  const res = await fetch(
    `${API_BASE}/api/missions/templates/${encodeURIComponent(templateId)}/instantiate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  return handleJson<InstantiateTemplateResponse>(res);
}
