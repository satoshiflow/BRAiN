export const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://localhost:8000"

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`

  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options?.headers,
    },
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}
