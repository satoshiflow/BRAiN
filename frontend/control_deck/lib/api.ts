export const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://localhost:8000"

export async function fetchJson<T>(path: string): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`

  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}
