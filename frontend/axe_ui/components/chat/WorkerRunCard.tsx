"use client";

import { memo } from "react";

import { WorkerApprovalPanel } from "@/components/chat/WorkerApprovalPanel";
import type { AxeWorkerArtifact, AxeWorkerUpdate } from "@/lib/contracts";

const statusStyles: Record<AxeWorkerUpdate["status"], string> = {
  queued: "border-slate-600 bg-slate-900/80 text-slate-200",
  running: "border-cyan-400/35 bg-cyan-500/10 text-cyan-100",
  waiting_input: "border-amber-300/60 bg-amber-500/15 text-amber-100",
  completed: "border-emerald-400/35 bg-emerald-500/10 text-emerald-100",
  failed: "border-rose-300/60 bg-rose-500/15 text-rose-100",
};

function WorkerRunCardComponent({
  update,
  onApprove,
  onReject,
}: {
  update: AxeWorkerUpdate;
  onApprove?: (workerRunId: string, reason: string) => void;
  onReject?: (workerRunId: string, reason: string) => void;
}) {
  const artifacts = update.artifacts ?? [];
  const inlineArtifacts = artifacts.filter((artifact) => artifact.content);
  const metricArtifact = artifacts.find((artifact) => artifact.type === "report");
  const metrics = metricArtifact?.metadata ?? {};
  const runtimeSourceArtifact = artifacts.find((artifact) => artifact.type === "runtime_source");
  const routingArtifact = artifacts.find((artifact) => artifact.type === "routing_decision");
  const approvalArtifact = artifacts.find((artifact) => artifact.type === "approval");
  const pendingRequestArtifact = artifacts.find((artifact) => artifact.type === "pending_request");
  const approvalHistoryArtifact = artifacts.find(
    (artifact) => artifact.type === "approval_history" || (artifact.type === "approval" && artifact.metadata?.rejected === true),
  );
  const approvalRequired = approvalArtifact?.metadata?.approval_required === true && update.status === "waiting_input";

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
            {update.activity_source}
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
        {metrics.should_escalate === true && (
          <span className="rounded-full border border-amber-300/50 bg-amber-500/10 px-2 py-1 text-amber-100">
            escalation recommended
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

      {routingArtifact && <RoutingDecisionBlock artifact={routingArtifact} />}
      {runtimeSourceArtifact && <RuntimeSourceBlock artifact={runtimeSourceArtifact} />}

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

      {approvalRequired && (
        <WorkerApprovalPanel
          workerRunId={update.worker_run_id}
          approvalArtifact={approvalArtifact}
          pendingRequestArtifact={pendingRequestArtifact}
          onApprove={onApprove}
          onReject={onReject}
        />
      )}

      {approvalHistoryArtifact && !approvalRequired && (
        <ApprovalHistoryBlock artifact={approvalHistoryArtifact} />
      )}
    </div>
  );
}

function RuntimeSourceBlock({ artifact }: { artifact: AxeWorkerArtifact }) {
  const metadata = artifact?.metadata ?? {};
  const source = typeof metadata.source === "string" ? metadata.source : null;
  const taskId = typeof metadata.task_id === "string" ? metadata.task_id : null;
  const skillRunId = typeof metadata.skill_run_id === "string" ? metadata.skill_run_id : null;

  return (
    <div className="mt-3 rounded-lg border border-current/15 bg-black/10 p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Runtime source</p>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] opacity-85">
        {source && <span className="rounded-full border border-current/15 px-2 py-1">Source: {source}</span>}
        {taskId && <span className="rounded-full border border-current/15 px-2 py-1">Task: {taskId}</span>}
        {skillRunId && <span className="rounded-full border border-current/15 px-2 py-1">SkillRun: {skillRunId}</span>}
      </div>
    </div>
  );
}

function RoutingDecisionBlock({ artifact }: { artifact: AxeWorkerArtifact }) {
  const metadata = artifact?.metadata ?? {};
  const routingDecisionId = typeof metadata.routing_decision_id === "string" ? metadata.routing_decision_id : null;
  const selectedWorker = typeof metadata.selected_worker === "string" ? metadata.selected_worker : null;
  const strategy = typeof metadata.strategy === "string" ? metadata.strategy : null;

  return (
    <div className="mt-3 rounded-lg border border-current/15 bg-black/10 p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Routing decision</p>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] opacity-85">
        {routingDecisionId && <span className="rounded-full border border-current/15 px-2 py-1">ID: {routingDecisionId}</span>}
        {selectedWorker && <span className="rounded-full border border-current/15 px-2 py-1">Selected: {selectedWorker}</span>}
        {strategy && <span className="rounded-full border border-current/15 px-2 py-1">Strategy: {strategy}</span>}
      </div>
    </div>
  );
}

function ApprovalHistoryBlock({ artifact }: { artifact: AxeWorkerArtifact }) {
  const metadata = artifact?.metadata ?? {};
  const isRejected = metadata.rejected === true;
  const approved = metadata.approved === true;
  const decidedBy = typeof metadata.decided_by === "string" ? metadata.decided_by : null;
  const decidedAt = typeof metadata.decided_at === "string" ? metadata.decided_at : null;
  const reason = typeof metadata.reason === "string"
    ? metadata.reason
    : typeof metadata.approval_reason === "string"
      ? metadata.approval_reason
      : typeof metadata.rejection_reason === "string"
        ? metadata.rejection_reason
        : null;

  return (
    <div className="mt-3 rounded-lg border border-current/15 bg-black/10 p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Approval history</p>
      <p className="mt-2 text-sm opacity-90">
        {approved ? "Approved" : isRejected ? "Rejected" : artifact.label}
      </p>
      {reason && <p className="mt-2 text-xs leading-5 opacity-80">{reason}</p>}
      {(decidedBy || decidedAt) && (
        <div className="mt-2 flex flex-wrap gap-2 text-[11px] opacity-75">
          {decidedBy && <span className="rounded-full border border-current/15 px-2 py-1">Actor: {decidedBy}</span>}
          {decidedAt && (
            <span className="rounded-full border border-current/15 px-2 py-1">
              Time: {new Date(decidedAt).toLocaleString()}
            </span>
          )}
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
