"use client"

import { ThreatStatusControl } from "@/components/ThreatStatusControl"

type ThreatSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
type ThreatStatus = "OPEN" | "INVESTIGATING" | "MITIGATED" | "IGNORED" | "ESCALATED"

export type Threat = {
  id: string
  type: string
  source: string
  severity: ThreatSeverity
  status: ThreatStatus
  description?: string | null
  metadata: Record<string, unknown>
  created_at: number
  last_seen_at: number
}

type ThreatTableProps = {
  threats: Threat[]
}

export function ThreatTable({ threats }: ThreatTableProps) {
  if (!threats.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400">
        Aktuell keine Threats registriert.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/80">
      <div className="max-h-[460px] overflow-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="sticky top-0 bg-slate-900">
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="px-3 py-2 font-medium">ID</th>
              <th className="px-3 py-2 font-medium">Type</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Severity</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Description</th>
              <th className="px-3 py-2 font-medium">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {threats.map((t) => (
              <tr
                key={t.id}
                className="border-b border-slate-900/60 text-slate-200 hover:bg-slate-900/80"
              >
                <td className="px-3 py-2 font-mono text-[10px] text-slate-400">
                  {t.id.slice(0, 8)}…
                </td>
                <td className="px-3 py-2 text-slate-200">{t.type}</td>
                <td className="px-3 py-2 text-slate-400">{t.source}</td>
                <td className="px-3 py-2">
                  <SeverityBadge severity={t.severity} />
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <StatusBadge status={t.status} />
                    <ThreatStatusControl
                      threatId={t.id}
                      currentStatus={t.status}
                    />
                  </div>
                </td>
                <td className="px-3 py-2 text-slate-300">
                  {t.description || <span className="text-slate-500">–</span>}
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-slate-400">
                  {new Date(t.last_seen_at * 1000).toLocaleString("de-DE")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: ThreatSeverity }) {
  let className = "bg-slate-800 text-slate-100"

  if (severity === "LOW") {
    className = "bg-emerald-900/60 text-emerald-300"
  } else if (severity === "MEDIUM") {
    className = "bg-amber-900/60 text-amber-300"
  } else if (severity === "HIGH") {
    className = "bg-orange-900/60 text-orange-300"
  } else if (severity === "CRITICAL") {
    className = "bg-rose-900/60 text-rose-300"
  }

  return (
    <span className={`rounded-full px-2 py-1 text-[10px] uppercase ${className}`}>
      {severity}
    </span>
  )
}

function StatusBadge({ status }: { status: ThreatStatus }) {
  let className = "bg-slate-800 text-slate-100"

  if (status === "OPEN") {
    className = "bg-rose-900/60 text-rose-300"
  } else if (status === "INVESTIGATING") {
    className = "bg-sky-900/60 text-sky-300"
  } else if (status === "MITIGATED") {
    className = "bg-emerald-900/60 text-emerald-300"
  } else if (status === "IGNORED") {
    className = "bg-slate-800 text-slate-300"
  } else if (status === "ESCALATED") {
    className = "bg-fuchsia-900/60 text-fuchsia-300"
  }

  return (
    <span className={`rounded-full px-2 py-1 text-[10px] uppercase ${className}`}>
      {status}
    </span>
  )
}