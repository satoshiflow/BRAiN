"use client";

import { useEffect, useState, useCallback } from "react";
import { neuralApi, type BrainParameter, type BrainState, type NeuralExecution, type NeuralStats } from "@/lib/api/neural";
import { cn, formatRelativeTime, formatDuration } from "@/lib/utils";

const presetStates: BrainState[] = [
  {
    name: "default",
    description: "Standard BRAiN Verhalten",
    parameters: { creativity: 0.7, caution: 0.5, speed: 0.8 },
    isDefault: true,
  },
  {
    name: "creative",
    description: "Höhere Kreativität, mehr Experimente",
    parameters: { creativity: 0.95, caution: 0.2, speed: 0.6 },
  },
  {
    name: "fast",
    description: "Schnelle Ausführung, weniger Analyse",
    parameters: { creativity: 0.4, caution: 0.7, speed: 0.95 },
  },
  {
    name: "safe",
    description: "Maximale Vorsicht, gründliche Prüfung",
    parameters: { creativity: 0.3, caution: 0.95, speed: 0.5 },
  },
];

function ParameterSlider({
  parameter,
  onChange,
}: {
  parameter: BrainParameter;
  onChange: (key: string, value: number) => void;
}) {
  const [localValue, setLocalValue] = useState(parameter.value);
  const [isUpdating, setIsUpdating] = useState(false);

  const handleChange = (newValue: number) => {
    setLocalValue(newValue);
    setIsUpdating(true);
    onChange(parameter.key, newValue);
    setTimeout(() => setIsUpdating(false), 500);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {parameter.key}
        </label>
        <div className="flex items-center gap-2">
          {isUpdating && (
            <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          )}
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {(localValue * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <input
        type="range"
        min={parameter.min}
        max={parameter.max}
        step={0.01}
        value={localValue}
        onChange={(e) => handleChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer"
      />
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {parameter.description}
      </p>
    </div>
  );
}

function ExecutionCard({ execution }: { execution: NeuralExecution }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              execution.success ? "bg-green-500" : "bg-red-500"
            )}
          />
          <div>
            <p className="font-medium text-slate-900 dark:text-slate-100">
              {execution.action}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {formatRelativeTime(execution.timestamp)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {execution.duration && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {formatDuration(execution.duration)}
            </span>
          )}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={cn("transition-transform", isExpanded && "rotate-180")}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-500 dark:text-slate-400">Parameter</p>
              <pre className="mt-1 text-xs bg-slate-100 dark:bg-slate-900 p-2 rounded overflow-x-auto">
                {JSON.stringify(execution.parameters, null, 2)}
              </pre>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400">Ergebnis</p>
              <pre className="mt-1 text-xs bg-slate-100 dark:bg-slate-900 p-2 rounded overflow-x-auto">
                {execution.result || "Keine Details"}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function NeuralPage() {
  const [parameters, setParameters] = useState<BrainParameter[]>([]);
  const [executions, setExecutions] = useState<NeuralExecution[]>([]);
  const [stats, setStats] = useState<NeuralStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"parameters" | "executions">("parameters");

  const fetchData = useCallback(async () => {
    try {
      const [params, execs, statsData] = await Promise.all([
        neuralApi.getParameters(),
        neuralApi.getExecutions(20),
        neuralApi.getStats(),
      ]);
      setParameters(params);
      setExecutions(execs);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch neural data:", err);
      setError("Konnte Neural-Daten nicht laden");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleParameterChange = async (key: string, value: number) => {
    setSaving(true);
    try {
      await neuralApi.updateParameter(key, value);
      setParameters((prev) =>
        prev.map((p) => (p.key === key ? { ...p, value } : p))
      );
      setActivePreset(null);
    } catch (err) {
      console.error("Failed to update parameter:", err);
      setError("Parameter konnte nicht gespeichert werden");
    } finally {
      setSaving(false);
    }
  };

  const handlePresetApply = async (preset: BrainState) => {
    setSaving(true);
    setActivePreset(preset.name);
    try {
      await neuralApi.applyState(preset.name);
      setParameters((prev) =>
        prev.map((p) => ({
          ...p,
          value: preset.parameters[p.key] ?? p.value,
        }))
      );
    } catch (err) {
      console.error("Failed to apply preset:", err);
      setError("Preset konnte nicht angewendet werden");
      setActivePreset(null);
    } finally {
      setSaving(false);
    }
  };

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

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-1">
          Neural Core Parameter
        </h3>
        <p className="text-sm text-blue-700 dark:text-blue-300">
          Justieren Sie die kognitiven Parameter von BRAiN zur Laufzeit. Änderungen werden
          sofort wirksam.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Ausführungen gesamt</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {stats.totalExecutions}
            </p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Ø Dauer</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {stats.avgDuration > 0 ? formatDuration(Math.floor(stats.avgDuration)) : "-"}
            </p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">Erfolgsrate</p>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">
              {(stats.successRate * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      )}

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab("parameters")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "parameters"
              ? "border-blue-600 text-blue-600 dark:text-blue-400"
              : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          )}
        >
          Parameter
        </button>
        <button
          onClick={() => setActiveTab("executions")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "executions"
              ? "border-blue-600 text-blue-600 dark:text-blue-400"
              : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          )}
        >
          Verlauf ({executions.length})
        </button>
      </div>

      {activeTab === "parameters" && (
        <>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Presets
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {presetStates.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => handlePresetApply(preset)}
                  disabled={saving}
                  className={cn(
                    "p-4 rounded-lg border text-left transition-colors",
                    activePreset === preset.name
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
                      : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600",
                    "disabled:opacity-50"
                  )}
                >
                  <p className="font-medium text-slate-900 dark:text-slate-100 capitalize">
                    {preset.name}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {preset.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Parameter
            </h3>
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
              <div className="space-y-6">
                {parameters.map((param) => (
                  <ParameterSlider
                    key={param.key}
                    parameter={param}
                    onChange={handleParameterChange}
                  />
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === "executions" && (
        <div className="space-y-4">
          {executions.length === 0 ? (
            <p className="text-center text-slate-500 dark:text-slate-400 py-8">
              Keine Ausführungen gefunden
            </p>
          ) : (
            executions.map((execution) => (
              <ExecutionCard key={execution.id} execution={execution} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
