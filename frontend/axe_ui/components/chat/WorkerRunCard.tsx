"use client";

import { memo } from "react";

import type { AxeWorkerUpdate } from "@/lib/contracts";

const statusStyles: Record<AxeWorkerUpdate["status"], string> = {
  queued: "border-slate-600 bg-slate-900/80 text-slate-200",
  running: "border-cyan-400/35 bg-cyan-500/10 text-cyan-100",
  waiting_input: "border-amber-400/35 bg-amber-500/10 text-amber-100",
  completed: "border-emerald-400/35 bg-emerald-500/10 text-emerald-100",
  failed: "border-rose-400/35 bg-rose-500/10 text-rose-100",
};

function WorkerRunCardComponent({ update }: { update: AxeWorkerUpdate }) {
  const artifacts = update.artifacts ?? [];
  const inlineArtifacts = artifacts.filter((artifact) => artifact.content);
  const metricArtifact = artifacts.find((artifact) => artifact.type === "report");
  const metrics = metricArtifact?.metadata ?? {};

  return (
    <div className={`mt-3 rounded-xl border p-3 ${statusStyles[update.status]}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] opacity-70">Worker status</p>
          <p className="text-sm font-semibold">{update.label}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className="rounded-full border border-current/25 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em]">
            {update.worker_type}
          </span>
          <span className="rounded-full border border-current/25 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em]">
            {update.status}
          </span>
        </div>
      </div>

      <p className="mt-2 text-sm opacity-90">{update.detail}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs opacity-75">
        <span>{new Date(update.updated_at).toLocaleTimeString()}</span>
        <span className="rounded-full border border-current/15 px-2 py-1">{update.worker_run_id}</span>
        {typeof metrics.estimated_cost_credits === "number" && (
          <span className="rounded-full border border-current/15 px-2 py-1">
            {metrics.estimated_cost_credits.toFixed(2)} credits
          </span>
        )}
        {typeof metrics.approx_peak_rss_mb === "number" && (
          <span className="rounded-full border border-current/15 px-2 py-1">
            {metrics.approx_peak_rss_mb.toFixed(1)} MB rss
          </span>
        )}
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

      {inlineArtifacts.length > 0 && (
        <div className="mt-3 space-y-3">
          {inlineArtifacts.map((artifact) => (
            <div key={`${artifact.type}-${artifact.label}-inline`} className="rounded-lg border border-current/15 bg-black/10 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] opacity-75">{artifact.label}</p>
              {artifact.type === "patch" ? (
                <DiffArtifactView content={artifact.content ?? ""} />
              ) : (
                <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 opacity-95">{artifact.content}</pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DiffArtifactView({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <div className="overflow-x-auto rounded-md border border-current/10 bg-slate-950/70">
      <div className="min-w-full font-mono text-xs leading-5">
        {lines.map((line, index) => {
          const isAddition = line.startsWith("+");
          const isRemoval = line.startsWith("-");
          const isHunk = line.startsWith("@@");
          const rowClass = isAddition
            ? "bg-emerald-500/10 text-emerald-100"
            : isRemoval
              ? "bg-rose-500/10 text-rose-100"
              : isHunk
                ? "bg-cyan-500/10 text-cyan-100"
                : "text-slate-200";

          return (
            <div key={`${index}-${line}`} className={`grid grid-cols-[3rem_1fr] gap-3 px-3 py-1 ${rowClass}`}>
              <span className="select-none text-right opacity-40">{index + 1}</span>
              <span className="whitespace-pre-wrap break-words">{line || " "}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const WorkerRunCard = memo(WorkerRunCardComponent);
