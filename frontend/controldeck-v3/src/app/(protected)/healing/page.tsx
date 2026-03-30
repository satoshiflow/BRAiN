"use client";

import { useEffect, useState, useCallback } from "react";
import { immuneApi, type ImmuneEvent, type ImmuneStats } from "@/lib/api/immune";
import { cn, formatRelativeTime, formatDuration } from "@/lib/utils";
import { HelpHint } from "@/components/help/help-hint";
import { getControlDeckHelpTopic } from "@/lib/help/topics";

interface ImmuneStreamPayload {
  audit?: Array<{
    audit_id: string;
    event_type: string;
    action: string;
    severity: "critical" | "warning" | "info";
    resource_type: string;
    resource_id: string;
    details?: Record<string, unknown>;
    timestamp: string;
  }>;
}

type ManualAction = "retry" | "skip" | "escalate";

interface ActionTimelineEntry {
  id: string;
  timestamp: string;
  requestedAction: ManualAction;
  resultingDecision: string;
  reason: string;
  target: string;
  priorityScore: number;
}

function getActionLabels(event: ImmuneEvent): Record<ManualAction, string> {
  if (event.severity === "critical") {
    return {
      retry: "Sofort neu bewerten",
      skip: "Als bekannt markieren",
      escalate: "An Governance eskalieren",
    };
  }

  if (event.severity === "warning") {
    return {
      retry: "Neu bewerten",
      skip: "Temporär ignorieren",
      escalate: "Zur Prüfung eskalieren",
    };
  }

  return {
    retry: "Signal verifizieren",
    skip: "Ignorieren",
    escalate: "Eskalieren",
  };
}

function SeverityBadge({ severity }: { severity: ImmuneEvent["severity"] }) {
  const styles = {
    critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    warning: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    info: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        styles[severity]
      )}
    >
      {severity.toUpperCase()}
    </span>
  );
}

function StatusBadge({ status }: { status: ImmuneEvent["status"] }) {
  const styles = {
    pending: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
    in_progress: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    resolved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    skipped: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
  };

  const labels = {
    pending: "Ausstehend",
    in_progress: "In Bearbeitung",
    resolved: "Gelöst",
    failed: "Fehlgeschlagen",
    skipped: "Übersprungen",
  };

  return (
    <span className={cn("text-xs", styles[status])}>{labels[status]}</span>
  );
}

function ActionButtons({ 
  event, 
  onAction 
}: { 
  event: ImmuneEvent; 
  onAction: (event: ImmuneEvent, action: ManualAction) => void;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const labels = getActionLabels(event);

  const handleAction = async (action: ManualAction) => {
    setIsLoading(true);
    try {
      await onAction(event, action);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex gap-2 mt-2">
      <button
        onClick={() => handleAction("retry")}
        disabled={isLoading}
        className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50"
      >
        {labels.retry}
      </button>
      <button
        onClick={() => handleAction("skip")}
        disabled={isLoading}
        className="px-2 py-1 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50"
      >
        {labels.skip}
      </button>
      <button
        onClick={() => handleAction("escalate")}
        disabled={isLoading}
        className="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50"
      >
        {labels.escalate}
      </button>
    </div>
  );
}

export default function HealingPage() {
  const [events, setEvents] = useState<ImmuneEvent[]>([]);
  const [stats, setStats] = useState<ImmuneStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionTimeline, setActionTimeline] = useState<ActionTimelineEntry[]>([]);
  const [highlightedEventId, setHighlightedEventId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "critical" | "warning" | "info">("all");
  const [isStreaming, setIsStreaming] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [eventsData, statsData] = await Promise.all([
        immuneApi.getEvents(50),
        immuneApi.getStats(),
      ]);
      setEvents(eventsData);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch immune data:", err);
      setError("Konnte Immune-Daten nicht laden");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleAction = async (event: ImmuneEvent, action: ManualAction) => {
    try {
      const result = await immuneApi.triggerAction({ eventId: event.id, action, event });
      setActionMessage(`Aktion ausgefuehrt: ${result.decision.action} (${event.component})`);
      setHighlightedEventId(event.id);
      setActionTimeline((prev) => [
        {
          id: result.decision.decision_id,
          timestamp: result.decision.created_at,
          requestedAction: action,
          resultingDecision: result.decision.action,
          reason: result.decision.reason,
          target: event.component,
          priorityScore: result.decision.priority_score,
        },
        ...prev,
      ].slice(0, 8));
      await fetchData();
    } catch (err) {
      console.error("Failed to trigger action:", err);
      setError(`Aktion fehlgeschlagen: ${action}`);
    } finally {
      setTimeout(() => setActionMessage(null), 3500);
      setTimeout(() => setHighlightedEventId(null), 4500);
    }
  };

  useEffect(() => {
    let eventSource: EventSource | null = null;

    const initEventSource = () => {
      try {
        eventSource = immuneApi.subscribe();
        setIsStreaming(true);

        eventSource.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data) as ImmuneStreamPayload;
            if (parsed.audit && Array.isArray(parsed.audit)) {
              const nextEvents = parsed.audit.map((entry) => immuneApi.mapAuditEntry(entry));
              setEvents(nextEvents.slice(0, 50));
            }
          } catch (parseErr) {
            console.error("Failed to parse immune event:", parseErr);
          }
        };

        eventSource.onerror = () => {
          setIsStreaming(false);
          eventSource?.close();
        };
      } catch (err) {
        console.error("Failed to init event source:", err);
        setIsStreaming(false);
      }
    };

    fetchData().then(() => {
      if (typeof window !== "undefined") {
        initEventSource();
      }
    });

    const fallbackInterval = setInterval(async () => {
      if (!isStreaming) {
        await fetchData();
      }
    }, 30000);

    return () => {
      eventSource?.close();
      clearInterval(fallbackInterval);
    };
  }, [fetchData, isStreaming]);

  const filteredEvents = events.filter(
    (e) => filter === "all" || e.severity === filter
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 dark:text-slate-400">Laden...</p>
        </div>
      </div>
    );
  }

  if (error && !events.length) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-2 px-4 py-2 text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-md hover:bg-red-200 dark:hover:bg-red-900/50"
        >
          Erneut versuchen
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <div className="flex items-center gap-2">
              <span className={cn("w-2 h-2 rounded-full", isStreaming ? "bg-green-500 animate-pulse" : "bg-yellow-500")} />
              <p className="text-sm text-slate-500 dark:text-slate-400">Ereignisse gesamt</p>
            </div>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {stats.totalEvents}
            </p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Critical</p>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {stats.criticalCount}
            </p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Warning</p>
            <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {stats.warningCount}
            </p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Erfolgsrate</p>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">
              {(stats.successRate * 100).toFixed(0)}%
            </p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Ø Erholungszeit</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {stats.avgRecoveryTime > 0 ? formatDuration(Math.floor(stats.avgRecoveryTime)) : "-"}
            </p>
          </div>
        </div>
      )}


      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Self-Healing</h1>
        {(() => {
          const topic = getControlDeckHelpTopic("healing.actions");
          return topic ? <HelpHint topic={topic} /> : null;
        })()}
      </div>

      {error && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
          <p className="text-sm text-yellow-700 dark:text-yellow-400">{error}</p>
        </div>
      )}

      {actionMessage && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
          <p className="text-sm text-green-700 dark:text-green-400">{actionMessage}</p>
        </div>
      )}

      {actionTimeline.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">
            Letzte manuelle Entscheidungen
          </h4>
          <div className="space-y-2">
            {actionTimeline.map((entry) => (
              <div
                key={entry.id}
                className="rounded-md border border-slate-200 dark:border-slate-700 px-3 py-2 bg-slate-50 dark:bg-slate-900/40"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    <span className="font-medium">{entry.requestedAction}</span>
                    {" -> "}
                    <span className="font-medium">{entry.resultingDecision}</span>
                    {" · "}
                    {entry.target}
                  </p>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">
                    {formatRelativeTime(entry.timestamp)}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                  Score {entry.priorityScore.toFixed(2)} · {entry.reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Self-Healing Ereignisse
          </h3>
          <div className="flex gap-2">
            {(["all", "critical", "warning", "info"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "px-3 py-1 text-sm rounded-md transition-colors",
                  filter === f
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                )}
              >
                {f === "all" ? "Alle" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="divide-y divide-slate-200 dark:divide-slate-700">
            {filteredEvents.length === 0 ? (
              <p className="p-8 text-center text-slate-500 dark:text-slate-400">
                Keine Ereignisse gefunden
              </p>
            ) : (
              filteredEvents.map((event) => (
                <div
                  key={event.id}
                  className={cn(
                    "p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-shadow",
                    highlightedEventId === event.id && "ring-2 ring-blue-400/70 dark:ring-blue-500/60 bg-blue-50/40 dark:bg-blue-900/10"
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <SeverityBadge severity={event.severity} />
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {event.component}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {event.action}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                        {event.trigger} • {formatRelativeTime(event.timestamp)}
                      </p>
                      <ActionButtons event={event} onAction={handleAction} />
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <StatusBadge status={event.status} />
                      {event.duration && (
                        <span className="text-xs text-slate-500 dark:text-slate-500">
                          {formatDuration(event.duration)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
