"use client";

import type { AxeWorkerUpdate } from "@/lib/contracts";

const statusStyles: Record<AxeWorkerUpdate["status"], string> = {
  queued: "border-slate-600 bg-slate-900/80 text-slate-200",
  running: "border-cyan-400/35 bg-cyan-500/10 text-cyan-100",
  waiting_input: "border-amber-400/35 bg-amber-500/10 text-amber-100",
  completed: "border-emerald-400/35 bg-emerald-500/10 text-emerald-100",
  failed: "border-rose-400/35 bg-rose-500/10 text-rose-100",
};

export function WorkerRunCard({ update }: { update: AxeWorkerUpdate }) {
  const artifacts = update.artifacts ?? [];

  return (
    <div className={`mt-3 rounded-xl border p-3 ${statusStyles[update.status]}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] opacity-70">Worker status</p>
          <p className="text-sm font-semibold">{update.label}</p>
        </div>
        <span className="rounded-full border border-current/25 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em]">
          {update.status}
        </span>
      </div>

      <p className="mt-2 text-sm opacity-90">{update.detail}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs opacity-75">
        <span>{new Date(update.updated_at).toLocaleTimeString()}</span>
        <span className="rounded-full border border-current/15 px-2 py-1">{update.worker_run_id}</span>
      </div>

      {artifacts.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {artifacts.map((artifact) => (
            <span key={`${artifact.type}-${artifact.label}`} className="rounded-full border border-current/15 px-2.5 py-1 text-xs">
              {artifact.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
