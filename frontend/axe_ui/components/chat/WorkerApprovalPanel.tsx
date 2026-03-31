"use client";

import { useMemo, useState } from "react";

import type { AxeWorkerArtifact } from "@/lib/contracts";

interface WorkerApprovalPanelProps {
  workerRunId: string;
  approvalArtifact?: AxeWorkerArtifact;
  pendingRequestArtifact?: AxeWorkerArtifact;
  onApprove?: (workerRunId: string, reason: string) => Promise<void> | void;
  onReject?: (workerRunId: string, reason: string) => Promise<void> | void;
}

export function WorkerApprovalPanel({
  workerRunId,
  approvalArtifact,
  pendingRequestArtifact,
  onApprove,
  onReject,
}: WorkerApprovalPanelProps) {
  const [approvalReason, setApprovalReason] = useState("Operator approved exact scoped edit");
  const [rejectionReason, setRejectionReason] = useState("Operator rejected bounded apply request");
  const [submittingAction, setSubmittingAction] = useState<"approve" | "reject" | null>(null);

  const approvalMeta = approvalArtifact?.metadata ?? {};
  const pendingMeta = pendingRequestArtifact?.metadata ?? {};
  const fileScope = Array.isArray(pendingMeta.file_scope)
    ? pendingMeta.file_scope.filter((value): value is string => typeof value === "string")
    : [];
  const executionMode = typeof approvalMeta.execution_mode === "string" ? approvalMeta.execution_mode : "bounded_apply";
  const workerType = typeof approvalMeta.worker_type === "string" ? approvalMeta.worker_type : "miniworker";

  const policyHints = useMemo(
    () => [
      `Mode: ${executionMode}`,
      `Worker: ${workerType}`,
      `Scope: ${fileScope.length > 0 ? `${fileScope.length} file(s)` : "no explicit file scope"}`,
      "Policy: approve only if the requested edit is narrow, reviewable, and expected.",
      "Risk: bounded_apply can change repository files immediately after approval.",
    ],
    [executionMode, fileScope.length, workerType],
  );

  const handleApprove = async () => {
    if (!onApprove || !approvalReason.trim() || submittingAction !== null) {
      return;
    }
    try {
      setSubmittingAction("approve");
      await onApprove(workerRunId, approvalReason.trim());
    } finally {
      setSubmittingAction(null);
    }
  };

  const handleReject = async () => {
    if (!onReject || !rejectionReason.trim() || submittingAction !== null) {
      return;
    }
    try {
      setSubmittingAction("reject");
      await onReject(workerRunId, rejectionReason.trim());
    } finally {
      setSubmittingAction(null);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-current/15 bg-black/10 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Approval Panel</p>
          <p className="mt-1 text-sm opacity-90">Review the bounded apply scope before allowing execution.</p>
        </div>
        <span className="rounded-full border border-current/15 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em]">
          human gate
        </span>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-current/10 bg-slate-950/60 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Policy hints</p>
          <div className="space-y-2 text-xs leading-5 opacity-90">
            {policyHints.map((hint) => (
              <p key={hint}>{hint}</p>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-current/10 bg-slate-950/60 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Scoped files</p>
          <div className="space-y-2 text-xs leading-5 opacity-90">
            {fileScope.length > 0 ? fileScope.map((path) => <p key={path}>{path}</p>) : <p>No explicit files recorded.</p>}
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Approval reason</p>
          <textarea
            value={approvalReason}
            onChange={(event) => setApprovalReason(event.target.value)}
            className="min-h-20 w-full rounded-md border border-current/15 bg-slate-950/70 px-3 py-2 text-sm text-current outline-none placeholder:text-current/40"
            placeholder="Explain why this bounded apply is approved"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleApprove}
              disabled={!approvalReason.trim() || submittingAction !== null}
              className="rounded-lg border border-emerald-300/35 bg-emerald-500/15 px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submittingAction === "approve" ? "Approving..." : "Approve apply"}
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] opacity-75">Rejection reason</p>
          <textarea
            value={rejectionReason}
            onChange={(event) => setRejectionReason(event.target.value)}
            className="min-h-20 w-full rounded-md border border-current/15 bg-slate-950/70 px-3 py-2 text-sm text-current outline-none placeholder:text-current/40"
            placeholder="Explain why this bounded apply is rejected"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleReject}
              disabled={!rejectionReason.trim() || submittingAction !== null}
              className="rounded-lg border border-rose-300/35 bg-rose-500/15 px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-rose-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submittingAction === "reject" ? "Rejecting..." : "Reject apply"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
