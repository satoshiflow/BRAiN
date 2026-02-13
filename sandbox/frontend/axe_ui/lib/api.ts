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
