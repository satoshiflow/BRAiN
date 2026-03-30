"use client";

import { useEffect, useState, useCallback } from "react";
import { healthApi, type HealthStatus, type ModuleHealth } from "@/lib/api/health";
import { cn, formatRelativeTime } from "@/lib/utils";

function StatusBadge({ status }: { status: ModuleHealth["status"] }) {
  const styles = {
    up: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    down: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    degraded: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  };

  const labels = {
    up: "Online",
    down: "Offline",
    degraded: "Beeinträchtigt",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        styles[status]
      )}
    >
      {labels[status]}
    </span>
  );
}

function ModuleCard({ module }: { module: ModuleHealth }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-slate-900 dark:text-slate-100">
            {module.name}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Zuletzt geprüft: {formatRelativeTime(module.lastCheck)}
          </p>
        </div>
        <StatusBadge status={module.status} />
      </div>

      {module.responseTime !== undefined && (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-slate-500 dark:text-slate-400">Antwortzeit</p>
            <p className="font-medium text-slate-900 dark:text-slate-100">
              {module.responseTime}ms
            </p>
          </div>
          {module.errorRate !== undefined && (
            <div>
              <p className="text-slate-500 dark:text-slate-400">Fehlerrate</p>
              <p
                className={cn(
                  "font-medium",
                  module.errorRate > 5
                    ? "text-red-600 dark:text-red-400"
                    : "text-slate-900 dark:text-slate-100"
                )}
              >
                {module.errorRate}%
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await healthApi.getStatus();
      setHealth(data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      console.error("Failed to fetch health:", err);
      setError("Konnte Health-Daten nicht laden");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let eventSource: EventSource | null = null;

    const initEventSource = () => {
      try {
        eventSource = healthApi.subscribe();
        setIsStreaming(true);

        eventSource.onopen = () => {
          console.log("Health stream connected");
        };

        eventSource.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data) as Record<string, unknown>;

            if (parsed && "overall" in parsed) {
              setHealth(parsed as unknown as HealthStatus);
              setLastUpdate(new Date());
              return;
            }

            if (parsed && "overall_status" in parsed) {
              const mapped = healthApi.mapStreamPayload(parsed as unknown as Parameters<typeof healthApi.mapStreamPayload>[0]);
              setHealth(mapped);
              setLastUpdate(new Date());
            }
          } catch (parseErr) {
            console.error("Failed to parse health event:", parseErr);
          }
        };

        eventSource.onerror = (err) => {
          console.error("Health stream error:", err);
          setIsStreaming(false);
          eventSource?.close();
          setTimeout(initEventSource, 5000);
        };
      } catch (err) {
        console.error("Failed to init event source:", err);
        setIsStreaming(false);
      }
    };

    fetchHealth().then(() => {
      if (typeof window !== "undefined") {
        initEventSource();
      }
    });

    const fallbackInterval = setInterval(async () => {
      if (!isStreaming) {
        await fetchHealth();
      }
    }, 30000);

    return () => {
      eventSource?.close();
      clearInterval(fallbackInterval);
    };
  }, [fetchHealth, isStreaming]);

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

  if (error || !health) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-sm text-red-600 dark:text-red-400">{error || "Keine Daten verfügbar"}</p>
        <button
          onClick={fetchHealth}
          className="mt-2 px-4 py-2 text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-md hover:bg-red-200 dark:hover:bg-red-900/50"
        >
          Erneut versuchen
        </button>
      </div>
    );
  }

  const statusColors = {
    healthy: "text-green-600 dark:text-green-400",
    degraded: "text-yellow-600 dark:text-yellow-400",
    critical: "text-red-600 dark:text-red-400",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              isStreaming ? "bg-green-500 animate-pulse" : "bg-yellow-500"
            )}
          />
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {isStreaming ? "Live" : "Polling"}
          </span>
        </div>
        {lastUpdate && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Letzte Aktualisierung: {lastUpdate.toLocaleTimeString("de-DE")}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">Systemstatus</p>
          <p className={cn("text-2xl font-bold capitalize", statusColors[health.overall])}>
            {health.overall}
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">Uptime</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {Math.floor(health.uptime / 3600)}h
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">Module</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {health.modules.length}
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">Version</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {health.version || "1.0.0"}
          </p>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Modul-Status
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {health.modules.map((module) => (
            <ModuleCard key={module.name} module={module} />
          ))}
        </div>
      </div>
    </div>
  );
}
