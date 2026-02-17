"use client"

import { useState } from "react"

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000"

const severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const
type Severity = (typeof severities)[number]

export function NewThreatForm() {
  const [type, setType] = useState("")
  const [source, setSource] = useState("")
  const [severity, setSeverity] = useState<Severity>("LOW")
  const [description, setDescription] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!type.trim() || !source.trim()) {
      setError("Type und Source dürfen nicht leer sein.")
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/threats`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          type,
          source,
          severity,
          description: description || null,
          metadata: {},
        }),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`API error ${res.status}: ${text}`)
      }

      const threat = await res.json()
      setSuccess(`Threat angelegt: ${threat.id}`)
      setType("")
      setSource("")
      setDescription("")
      setSeverity("LOW")
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unbekannter Fehler beim Anlegen.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
    >
      <div className="mb-3 text-sm font-medium text-slate-200">
        Neuen Threat registrieren
      </div>
      <div className="mb-3 grid gap-3 md:grid-cols-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Type</label>
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-emerald-500"
            value={type}
            onChange={(e) => setType(e.target.value)}
            placeholder="z.B. LLM_OUTPUT"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Source</label>
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-emerald-500"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="z.B. supervisor"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Severity</label>
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-emerald-500"
            value={severity}
            onChange={(e) => setSeverity(e.target.value as Severity)}
          >
            {severities.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mb-3 flex flex-col gap-1">
        <label className="text-xs text-slate-400">Description</label>
        <input
          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-emerald-500"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="optional"
        />
      </div>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={loading}
          className="rounded-md border border-emerald-500 bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading ? "Speichere..." : "Threat anlegen"}
        </button>
        {error && (
          <span className="text-xs text-rose-400">Fehler: {error}</span>
        )}
        {success && (
          <span className="text-xs text-emerald-400">{success}</span>
        )}
      </div>
      <div className="mt-2 text-xs text-slate-500">
        Nach dem Anlegen bitte die Seite neu laden, um den Threat in der Liste zu
        sehen.
      </div>
    </form>
  )
}