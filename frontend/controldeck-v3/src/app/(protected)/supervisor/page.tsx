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

function noteValue(item: DomainEscalationItem, key: string): string | null {
  const value = item.notes?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

export default function SupervisorInboxPage() {
  const topic = getControlDeckHelpTopic("supervisor.inbox");
  const searchParams = useSearchParams();
  const scope = searchParams.get("scope");
  const [items, setItems] = useState<DomainEscalationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | DomainEscalationStatus>("all");

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

  const scopedItems = useMemo(() => paperclipScoped(items, scope), [items, scope]);
  const statusCounts = useMemo(() => {
    return scopedItems.reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = (acc[item.status] ?? 0) + 1;
      return acc;
    }, {});
  }, [scopedItems]);

  const filtered = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return scopedItems.filter((item) => {
      if (statusFilter !== "all" && item.status !== statusFilter) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      const haystack = [
        item.escalation_id,
        item.domain_key,
        item.requested_by,
        noteValue(item, "action_request_id"),
        noteValue(item, "target_ref"),
        noteValue(item, "task_id"),
        noteValue(item, "skill_run_id"),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedSearch);
    });
  }, [scopedItems, search, statusFilter]);

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

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
          <label className="block">
            <span className="sr-only">Search escalations</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by escalation, domain, task, action request or skill run"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {([
              "all",
              "queued",
              "in_review",
              "approved",
              "denied",
              "cancelled",
            ] as const).map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setStatusFilter(status)}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium",
                  statusFilter === status
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
                )}
              >
                {status === "all" ? `all (${scopedItems.length})` : `${status} (${statusCounts[status] ?? 0})`}
              </button>
            ))}
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
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        {noteValue(item, "action_request_id") ? (
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                            action request: {noteValue(item, "action_request_id")}
                          </span>
                        ) : null}
                        {noteValue(item, "target_ref") ? (
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                            target: {noteValue(item, "target_ref")}
                          </span>
                        ) : null}
                      </div>
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
                      <div className="flex flex-col items-start gap-2">
                        <Link
                          href={`/supervisor/${encodeURIComponent(item.escalation_id)}`}
                          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                        >
                          Open
                        </Link>
                        {noteValue(item, "target_ref") ? (
                          <Link
                            href="/external-operations"
                            className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                          >
                            Open External Ops
                          </Link>
                        ) : null}
                      </div>
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
