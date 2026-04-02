"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { HelpHint } from "@/components/help/help-hint";
import { ApiError } from "@/lib/api/client";
import { getControlDeckHelpTopic } from "@/lib/help/topics";
import { supervisorApi, type DomainEscalationItem, type DomainEscalationStatus } from "@/lib/api/supervisor";
import { cn, formatRelativeTime } from "@/lib/utils";

const statusTone: Record<DomainEscalationStatus, string> = {
  queued: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  in_review: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  denied: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  cancelled: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
};

function paperclipScoped(items: DomainEscalationItem[], scope: string | null): DomainEscalationItem[] {
  if (scope !== "paperclip") {
    return items;
  }
  return items.filter((item) => item.domain_key.startsWith("external_apps.paperclip"));
}

export default function SupervisorInboxPage() {
  const topic = getControlDeckHelpTopic("supervisor.inbox");
  const searchParams = useSearchParams();
  const scope = searchParams.get("scope");
  const [items, setItems] = useState<DomainEscalationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const payload = await supervisorApi.listDomainEscalations(100);
      setItems(payload.items);
      setError(null);
    } catch (err) {
      console.error("Failed to load supervisor inbox", err);
      if (err instanceof ApiError) {
        setError(`Supervisor inbox failed to load (${err.status}).`);
      } else {
        setError("Supervisor inbox failed to load.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filtered = useMemo(() => paperclipScoped(items, scope), [items, scope]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-2">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Supervisor Inbox</h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Domain escalation handoffs for governed review. {scope === "paperclip" ? "Filtered to Paperclip external operations." : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {topic ? <HelpHint topic={topic} /> : null}
            <button
              type="button"
              onClick={loadData}
              className="rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      ) : null}

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
        {filtered.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Keine Eskalationen gefunden.</p>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                  <th className="py-2 pr-4 font-medium">Escalation</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium">Domain</th>
                  <th className="py-2 pr-4 font-medium">Risk</th>
                  <th className="py-2 pr-4 font-medium">Received</th>
                  <th className="py-2 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.escalation_id} className="border-b border-slate-100 dark:border-slate-800 align-top">
                    <td className="py-3 pr-4">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{item.escalation_id}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">requested by {item.requested_by}</p>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium", statusTone[item.status])}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-slate-600 dark:text-slate-300">{item.domain_key}</td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{item.risk_tier}</td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{formatRelativeTime(item.received_at)}</td>
                    <td className="py-3">
                      <Link
                        href={`/supervisor/${encodeURIComponent(item.escalation_id)}`}
                        className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
