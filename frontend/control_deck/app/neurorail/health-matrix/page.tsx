"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useState, useEffect } from "react";
import {
  fetchTelemetrySnapshot,
  type RealtimeSnapshot,
  formatErrorMessage,
} from "@/lib/neurorailApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
  lastUpdated?: string;
};

export default function HealthMatrixPage() {
  const [snapshotState, setSnapshotState] = useState<LoadState<RealtimeSnapshot>>({
    loading: true,
  });

  const [autoRefresh, setAutoRefresh] = useState(true);

  // Polling interval: 5 seconds
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    async function loadSnapshot() {
      try {
        const snapshot = await fetchTelemetrySnapshot();
        setSnapshotState({
          data: snapshot,
          loading: false,
          lastUpdated: new Date().toLocaleTimeString(),
        });
      } catch (err) {
        setSnapshotState({
          loading: false,
          error: formatErrorMessage(err),
        });
      }
    }

    // Initial load
    loadSnapshot();

    // Start polling if autoRefresh is enabled
    if (autoRefresh) {
      intervalId = setInterval(loadSnapshot, 5000); // 5 seconds
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [autoRefresh]);

  function renderEntityCounts() {
    if (!snapshotState.data) return null;

    const { entity_counts } = snapshotState.data;

    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Missions */}
        <div className="rounded-lg border border-blue-800 bg-blue-950/30 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-blue-400">Missions</h3>
            <span className="text-2xl font-bold text-blue-300">
              {entity_counts.missions}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500">Total missions</p>
        </div>

        {/* Plans */}
        <div className="rounded-lg border border-purple-800 bg-purple-950/30 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-purple-400">Plans</h3>
            <span className="text-2xl font-bold text-purple-300">
              {entity_counts.plans}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500">Total plans</p>
        </div>

        {/* Jobs */}
        <div className="rounded-lg border border-green-800 bg-green-950/30 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-green-400">Jobs</h3>
            <span className="text-2xl font-bold text-green-300">
              {entity_counts.jobs}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500">Total jobs</p>
        </div>

        {/* Attempts */}
        <div className="rounded-lg border border-amber-800 bg-amber-950/30 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-amber-400">Attempts</h3>
            <span className="text-2xl font-bold text-amber-300">
              {entity_counts.attempts}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500">Total attempts</p>
        </div>
      </div>
    );
  }

  function renderActiveExecutions() {
    if (!snapshotState.data?.active_executions) return null;

    const { running_attempts, queued_jobs } = snapshotState.data.active_executions;

    return (
      <div className="grid gap-4 md:grid-cols-2">
        {/* Running Attempts */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-400">Running Attempts</h3>
            <span
              className={`text-3xl font-bold ${
                running_attempts > 0 ? "text-green-400" : "text-gray-500"
              }`}
            >
              {running_attempts}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500">Currently executing</p>
        </div>

        {/* Queued Jobs */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-400">Queued Jobs</h3>
            <span
              className={`text-3xl font-bold ${
                queued_jobs > 0 ? "text-yellow-400" : "text-gray-500"
              }`}
            >
              {queued_jobs}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-500">Waiting to execute</p>
        </div>
      </div>
    );
  }

  function renderErrorRates() {
    if (!snapshotState.data?.error_rates) return null;

    const { mechanical_errors, ethical_errors } = snapshotState.data.error_rates;

    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-300">Error Rates</h3>
        <div className="space-y-4">
          {/* Mechanical Errors */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Mechanical Errors</span>
              <span className="font-mono text-sm font-medium text-orange-400">
                {(mechanical_errors * 100).toFixed(2)}%
              </span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded bg-gray-800">
              <div
                className="h-full bg-orange-500"
                style={{ width: `${Math.min(mechanical_errors * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Ethical Errors */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Ethical Errors</span>
              <span className="font-mono text-sm font-medium text-red-400">
                {(ethical_errors * 100).toFixed(2)}%
              </span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded bg-gray-800">
              <div
                className="h-full bg-red-500"
                style={{ width: `${Math.min(ethical_errors * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  function renderPrometheusMetrics() {
    if (!snapshotState.data?.prometheus_metrics) return null;

    const metrics = snapshotState.data.prometheus_metrics;

    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-300">
          Prometheus Metrics
        </h3>
        <div className="space-y-3">
          {Object.entries(metrics).map(([key, value]) => (
            <div
              key={key}
              className="flex items-center justify-between border-b border-gray-800 pb-2"
            >
              <span className="font-mono text-xs text-gray-400">{key}</span>
              <span className="font-mono text-sm font-medium text-blue-400">
                {typeof value === "number" ? value.toFixed(2) : value}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6 text-gray-100">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold text-blue-400">
            NeuroRail Health Matrix
          </h1>
          <p className="text-sm text-gray-400">
            Real-time system health and observability dashboard
          </p>
        </div>

        {/* Auto-refresh toggle */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="h-4 w-4 rounded border-gray-700 bg-gray-800 text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <label htmlFor="autoRefresh" className="text-sm text-gray-400">
              Auto-refresh (5s)
            </label>
          </div>

          {snapshotState.lastUpdated && (
            <div className="text-xs text-gray-500">
              Last updated: {snapshotState.lastUpdated}
            </div>
          )}

          {autoRefresh && (
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 animate-pulse rounded-full bg-green-500"></div>
              <span className="text-xs text-green-400">Live</span>
            </div>
          )}
        </div>
      </div>

      {/* Loading State */}
      {snapshotState.loading && !snapshotState.data && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-12 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-gray-700 border-t-blue-500"></div>
          <p className="mt-4 text-sm text-gray-400">Loading health data...</p>
        </div>
      )}

      {/* Error State */}
      {snapshotState.error && (
        <div className="mb-6 rounded border border-red-800 bg-red-950/30 p-4">
          <p className="text-sm font-medium text-red-400">
            ❌ Error: {snapshotState.error}
          </p>
        </div>
      )}

      {/* Data Display */}
      {snapshotState.data && (
        <div className="space-y-6">
          {/* Entity Counts KPIs */}
          <div>
            <h2 className="mb-4 text-xl font-bold text-blue-400">
              Entity Counts
            </h2>
            {renderEntityCounts()}
          </div>

          {/* Active Executions */}
          <div>
            <h2 className="mb-4 text-xl font-bold text-blue-400">
              Active Executions
            </h2>
            {renderActiveExecutions()}
          </div>

          {/* Error Rates */}
          <div>
            <h2 className="mb-4 text-xl font-bold text-blue-400">Error Rates</h2>
            {renderErrorRates()}
          </div>

          {/* Prometheus Metrics */}
          {snapshotState.data.prometheus_metrics &&
            Object.keys(snapshotState.data.prometheus_metrics).length > 0 && (
              <div>
                <h2 className="mb-4 text-xl font-bold text-blue-400">
                  System Metrics
                </h2>
                {renderPrometheusMetrics()}
              </div>
            )}

          {/* Timestamp */}
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-center">
            <p className="text-xs text-gray-500">
              Snapshot timestamp:{" "}
              <span className="font-mono text-gray-400">
                {snapshotState.data.timestamp}
              </span>
            </p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!snapshotState.data && !snapshotState.loading && !snapshotState.error && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-12 text-center">
          <p className="text-gray-400">
            No health data available. Enable auto-refresh to start monitoring.
          </p>
        </div>
      )}
    </div>
  );
}
