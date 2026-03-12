"use client";

import { useEffect, useMemo, useState } from "react";
import { getApiHealth } from "@/lib/api";
import { getApiBase } from "@/lib/config";
import { Tooltip } from "@/components/ui/tooltip";

type ApiHealthState = {
  status: "loading" | "ok" | "error";
  error: string | null;
};

export function ApiHealthIndicator() {
  const [apiHealth, setApiHealth] = useState<ApiHealthState>({
    status: "loading",
    error: null,
  });

  useEffect(() => {
    let active = true;

    const checkHealth = async () => {
      try {
        await getApiHealth();
        if (active) {
          setApiHealth({ status: "ok", error: null });
        }
      } catch (error) {
        if (active) {
          setApiHealth({
            status: "error",
            error: error instanceof Error ? error.message : "Unknown API error",
          });
        }
      }
    };

    void checkHealth();
    const interval = setInterval(() => {
      void checkHealth();
    }, 30000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const apiBase = getApiBase();
  const indicatorColorClass =
    apiHealth.status === "ok"
      ? "bg-emerald-500"
      : apiHealth.status === "error"
        ? "bg-red-500"
        : "bg-amber-400";

  const indicatorLabel =
    apiHealth.status === "ok"
      ? "API healthy"
      : apiHealth.status === "error"
        ? "API error"
        : "Checking API";

  const tooltipContent = useMemo(
    () => (
      <div className="space-y-1">
        <p className="font-semibold text-slate-100">{indicatorLabel}</p>
        <p className="text-slate-300">{apiBase}</p>
        {apiHealth.error && <p className="text-red-300">{apiHealth.error}</p>}
      </div>
    ),
    [apiBase, apiHealth.error, indicatorLabel]
  );

  return (
    <Tooltip content={tooltipContent}>
      <button
        type="button"
        className="mt-3 inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-3 py-1"
      >
        <span className={`h-2 w-2 rounded-full ${indicatorColorClass} animate-pulse`} />
        <span className="text-xs text-slate-300">{indicatorLabel}</span>
      </button>
    </Tooltip>
  );
}
