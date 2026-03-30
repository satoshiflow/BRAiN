"use client";

import { useEffect, useState, useCallback } from "react";
import { immuneApi, type ImmuneEvent, type ImmuneStats } from "@/lib/api/immune";
import { cn, formatRelativeTime, formatDuration } from "@/lib/utils";

interface ImmuneStreamEvent {
  type: "new_event" | "event_updated";
  data: ImmuneEvent;
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
  onAction: (eventId: string, action: "retry" | "skip" | "escalate") => void;
}) {
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async (action: "retry" | "skip" | "escalate") => {
    setIsLoading(true);
    try {
      await onAction(event.id, action);
    } finally {
      setIsLoading(false);
    }
  };

  if (event.status === "resolved") {
    return null;
  }

  return (
    <div className="flex gap-2 mt-2">
      {event.status === "failed" ? (
        <button
          onClick={() => handleAction("retry")}
          disabled={isLoading}
          className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50"
        >
          Wiederholen
        </button>
      ) : event.status === "skipped" ? null : (
        <>
          <button
            onClick={() => handleAction("skip")}
            disabled={isLoading}
            className="px-2 py-1 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50"
          >
            Überspringen
          </button>
          <button
            onClick={() => handleAction("escalate")}
            disabled={isLoading}
            className="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50"
          >
            Eskalieren
          </button>
        </>
      )}
    </div>
  );
}

export default function HealingPage() {
  const [events, setEvents] = useState<ImmuneEvent[]>([]);
  const [stats, setStats] = useState<ImmuneStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  const handleAction = async (eventId: string, action: "retry" | "skip" | "escalate") => {
    try {
      await immuneApi.triggerAction({ eventId, action });
      await fetchData();
    } catch (err) {
      console.error("Failed to trigger action:", err);
      setError(`Aktion fehlgeschlagen: ${action}`);
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
            const parsed = JSON.parse(event.data) as ImmuneStreamEvent;
            if (parsed.data) {
              setEvents((prev) => {
                const existing = prev.findIndex((e) => e.id === parsed.data.id);
                if (existing >= 0) {
                  const updated = [...prev];
                  updated[existing] = parsed.data;
                  return updated;
                }
                return [parsed.data, ...prev].slice(0, 50);
              });
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

      {error && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
          <p className="text-sm text-yellow-700 dark:text-yellow-400">{error}</p>
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
                <div key={event.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50">
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
