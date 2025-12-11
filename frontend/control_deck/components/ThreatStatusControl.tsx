"use client"

import { useState } from "react"

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000"

type ThreatStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "MITIGATED"
  | "IGNORED"
  | "ESCALATED"

type Props = {
  threatId: string
  currentStatus: ThreatStatus | string
}

export function ThreatStatusControl({ threatId, currentStatus }: Props) {
  const [status, setStatus] = useState<ThreatStatus | string>(currentStatus)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function updateStatus(newStatus: ThreatStatus) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/threats/${threatId}/status?status=${encodeURIComponent(
          newStatus,
        )}`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        },
      )

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`API error ${res.status}: ${text}`)
      }

      setStatus(newStatus)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Fehler beim Aktualisieren.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <select
        disabled={loading}
        className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] text-slate-100 outline-none focus:border-emerald-500"
        value={status}
        onChange={(e) => updateStatus(e.target.value as ThreatStatus)}
      >
        <option value="OPEN">OPEN</option>
        <option value="INVESTIGATING">INVESTIGATING</option>
        <option value="MITIGATED">MITIGATED</option>
        <option value="IGNORED">IGNORED</option>
        <option value="ESCALATED">ESCALATED</option>
      </select>
      {error && <span className="text-[10px] text-rose-400">{error}</span>}
    </div>
  )
}