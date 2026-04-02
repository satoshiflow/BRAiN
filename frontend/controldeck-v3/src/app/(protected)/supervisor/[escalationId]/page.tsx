"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HelpHint } from "@/components/help/help-hint";
import { DecisionDialog } from "@/components/operator/decision-dialog";
import { ApiError } from "@/lib/api/client";
import { getControlDeckHelpTopic } from "@/lib/help/topics";
import { supervisorApi, type DomainEscalationItem, type DomainEscalationStatus } from "@/lib/api/supervisor";

const nextDecisions: Array<{ status: DomainEscalationStatus; label: string }> = [
  { status: "in_review", label: "Mark in review" },
  { status: "approved", label: "Approve" },
  { status: "denied", label: "Deny" },
];

export default function SupervisorEscalationDetailPage() {
  const topic = getControlDeckHelpTopic("supervisor.decisions");
  const params = useParams<{ escalationId: string }>();
  const router = useRouter();
  const escalationId = decodeURIComponent(params.escalationId);
  const [item, setItem] = useState<DomainEscalationItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<DomainEscalationStatus | null>(null);

  const loadData = useCallback(async () => {
    try {
      const payload = await supervisorApi.getDomainEscalation(escalationId);
      setItem(payload);
      setError(null);
    } catch (err) {
      console.error("Failed to load supervisor escalation", err);
      if (err instanceof ApiError) {
        setError(`Supervisor escalation failed to load (${err.status}).`);
      } else {
        setError("Supervisor escalation failed to load.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [escalationId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDecision = useCallback(async (status: DomainEscalationStatus, reason: string) => {
    setIsSubmitting(true);
    try {
      await supervisorApi.decideDomainEscalation(escalationId, {
        status,
        decision_reason: reason,
        notes: { source: "controldeck_v3_supervisor" },
      });
      setPendingDecision(null);
      await loadData();
    } catch (err) {
      console.error("Failed to decide supervisor escalation", err);
      if (err instanceof ApiError) {
        setError(`Supervisor decision failed (${err.status}).`);
      } else {
        setError("Supervisor decision failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [escalationId, loadData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Supervisor escalation</p>
            {topic ? <HelpHint topic={topic} /> : null}
          </div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{escalationId}</h2>
        </div>
        <div className="flex gap-2">
          <Link
            href="/supervisor?scope=paperclip"
            className="rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
          >
            Back to inbox
          </Link>
          <button
            type="button"
            onClick={() => router.push("/external-operations")}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Back to External Ops
          </button>
        </div>
      </div>

      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      ) : null}

      {!item ? (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 text-sm text-slate-500 dark:text-slate-400">
          Escalation not found.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">Status</p>
              <p className="mt-2 font-medium text-slate-900 dark:text-slate-100">{item.status}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">Domain</p>
              <p className="mt-2 font-mono text-xs text-slate-900 dark:text-slate-100">{item.domain_key}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">Risk</p>
              <p className="mt-2 font-medium text-slate-900 dark:text-slate-100">{item.risk_tier}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">Requested by</p>
              <p className="mt-2 font-medium text-slate-900 dark:text-slate-100">{item.requested_by}</p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
            <h3 className="font-medium text-slate-900 dark:text-slate-100">Decision</h3>
            <div className="flex flex-wrap gap-2">
              {nextDecisions.map((decision) => (
                <button
                  key={decision.status}
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => setPendingDecision(decision.status)}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {decision.label}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
            <h3 className="font-medium text-slate-900 dark:text-slate-100">Escalation details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-slate-500 dark:text-slate-400">Received</p>
                <p className="text-slate-900 dark:text-slate-100">{item.received_at}</p>
              </div>
              <div>
                <p className="text-slate-500 dark:text-slate-400">Correlation</p>
                <p className="text-slate-900 dark:text-slate-100">{item.correlation_id ?? "-"}</p>
              </div>
              <div>
                <p className="text-slate-500 dark:text-slate-400">Reviewed by</p>
                <p className="text-slate-900 dark:text-slate-100">{item.reviewed_by ?? "-"}</p>
              </div>
              <div>
                <p className="text-slate-500 dark:text-slate-400">Review time</p>
                <p className="text-slate-900 dark:text-slate-100">{item.reviewed_at ?? "-"}</p>
              </div>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400 text-sm">Decision reason</p>
              <p className="text-sm text-slate-900 dark:text-slate-100">{item.decision_reason ?? "-"}</p>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400 text-sm">Notes</p>
              <pre className="mt-2 overflow-auto rounded-md bg-slate-50 dark:bg-slate-900 p-3 text-xs text-slate-700 dark:text-slate-200">
                {JSON.stringify(item.notes ?? {}, null, 2)}
              </pre>
            </div>
          </div>
        </>
      )}

      <DecisionDialog
        open={pendingDecision !== null}
        title="Record supervisor decision"
        description={pendingDecision ? `${pendingDecision} for ${escalationId}` : ""}
        confirmLabel="Save decision"
        initialReason={pendingDecision ? `${pendingDecision} via ControlDeck supervisor inbox` : ""}
        busy={isSubmitting}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDecision(null);
          }
        }}
        onConfirm={async (reason) => {
          if (!pendingDecision) {
            return;
          }
          await handleDecision(pendingDecision, reason);
        }}
      />
    </div>
  );
}
