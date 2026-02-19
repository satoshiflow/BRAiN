const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://127.0.0.1:8000";

export type AXEIdentity = {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  personality: Record<string, unknown>;
  capabilities: string[];
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
};

export type AXEIdentityCreate = {
  name: string;
  description?: string;
  system_prompt: string;
  personality?: Record<string, unknown>;
  capabilities?: string[];
};

export type AXEIdentityUpdate = Partial<AXEIdentityCreate>;

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as T;
}

// 7 Functions to implement:
export async function fetchIdentities(): Promise<AXEIdentity[]> {
  const res = await fetch(`${API_BASE}/api/axe/identity`);
  return handleResponse<AXEIdentity[]>(res);
}

export async function fetchActiveIdentity(): Promise<AXEIdentity> {
  const res = await fetch(`${API_BASE}/api/axe/identity/active`);
  return handleResponse<AXEIdentity>(res);
}

export async function fetchIdentity(id: string): Promise<AXEIdentity> {
  const res = await fetch(`${API_BASE}/api/axe/identity/${id}`);
  return handleResponse<AXEIdentity>(res);
}

export async function createIdentity(data: AXEIdentityCreate): Promise<AXEIdentity> {
  const res = await fetch(`${API_BASE}/api/axe/identity`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<AXEIdentity>(res);
}

export async function updateIdentity(id: string, data: AXEIdentityUpdate): Promise<AXEIdentity> {
  const res = await fetch(`${API_BASE}/api/axe/identity/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<AXEIdentity>(res);
}

export async function activateIdentity(id: string): Promise<AXEIdentity> {
  const res = await fetch(`${API_BASE}/api/axe/identity/${id}/activate`, {
    method: "POST",
  });
  return handleResponse<AXEIdentity>(res);
}

export async function deleteIdentity(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/axe/identity/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Delete failed: ${text}`);
  }
}
