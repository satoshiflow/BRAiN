// Skills API Client
// Client-side API functions for the PicoClaw-style Skill System

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://127.0.0.1:8000";

// ============================================================================
// Types
// ============================================================================

export type SkillCategory = "api" | "file" | "communication" | "analysis" | "custom";

export type SkillParameter = {
  name: string;
  type: "string" | "number" | "boolean" | "object" | "array";
  description?: string;
  required?: boolean;
  default?: unknown;
};

export type SkillManifest = {
  name: string;
  description?: string;
  category: SkillCategory;
  version?: string;
  parameters?: SkillParameter[];
  returns?: {
    type: string;
    description?: string;
  };
};

export type Skill = {
  id: string;
  name: string;
  description?: string | null;
  category: SkillCategory;
  manifest: SkillManifest;
  handler_path: string;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
};

export type CreateSkillPayload = {
  name: string;
  description?: string;
  category: SkillCategory;
  manifest: SkillManifest;
  handler_path: string;
  enabled?: boolean;
};

export type UpdateSkillPayload = Partial<CreateSkillPayload>;

export type SkillExecutionRequest = {
  parameters: Record<string, unknown>;
};

export type SkillExecutionResult = {
  success: boolean;
  output?: unknown;
  error?: string;
  execution_time_ms: number;
};

export type SkillsListResponse = {
  items: Skill[];
  total: number;
};

export type SkillCategoriesResponse = {
  categories: SkillCategory[];
};

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch all skills with optional filtering
 */
export async function fetchSkills(
  category?: SkillCategory | "all",
  search?: string
): Promise<SkillsListResponse> {
  const params = new URLSearchParams();
  if (category && category !== "all") params.append("category", category);
  if (search) params.append("search", search);
  
  const query = params.toString();
  const url = `${API_BASE}/api/skills${query ? `?${query}` : ""}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch skills: ${res.status}`);
  return res.json();
}

/**
 * Fetch a single skill by ID
 */
export async function fetchSkill(id: string): Promise<Skill> {
  const res = await fetch(`${API_BASE}/api/skills/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch skill: ${res.status}`);
  return res.json();
}

/**
 * Fetch all skill categories
 */
export async function fetchSkillCategories(): Promise<SkillCategoriesResponse> {
  const res = await fetch(`${API_BASE}/api/skills/categories`);
  if (!res.ok) throw new Error(`Failed to fetch categories: ${res.status}`);
  return res.json();
}

/**
 * Create a new skill
 */
export async function createSkill(payload: CreateSkillPayload): Promise<Skill> {
  const res = await fetch(`${API_BASE}/api/skills`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to create skill: ${err}`);
  }
  return res.json();
}

/**
 * Update an existing skill
 */
export async function updateSkill(
  id: string,
  payload: UpdateSkillPayload
): Promise<Skill> {
  const res = await fetch(`${API_BASE}/api/skills/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to update skill: ${err}`);
  }
  return res.json();
}

/**
 * Delete a skill
 */
export async function deleteSkill(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/skills/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete skill: ${res.status}`);
}

/**
 * Execute a skill with parameters
 */
export async function executeSkill(
  id: string,
  parameters: Record<string, unknown>
): Promise<SkillExecutionResult> {
  const res = await fetch(`${API_BASE}/api/skills/${id}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parameters }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to execute skill: ${err}`);
  }
  return res.json();
}
