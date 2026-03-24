const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export async function fetchJson<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: {
            "Accept": "application/json",
        },
        cache: "no-store",
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text}`);
    }

    return res.json() as Promise<T>;
}

export interface AxeUploadResponse {
    attachment_id: string;
    filename: string;
    mime_type: string;
    size_bytes: number;
    expires_at: string;
}

export interface AxeChatMessage {
    role: "system" | "user" | "assistant";
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

export async function uploadAttachment(file: File): Promise<AxeUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/axe/upload`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed ${res.status}: ${text}`);
    }

    return res.json() as Promise<AxeUploadResponse>;
}

export async function sendAxeChat(payload: AxeChatRequest): Promise<AxeChatResponse> {
    const res = await fetch(`${API_BASE}/api/axe/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Chat request failed ${res.status}: ${text}`);
    }

    return res.json() as Promise<AxeChatResponse>;
}
