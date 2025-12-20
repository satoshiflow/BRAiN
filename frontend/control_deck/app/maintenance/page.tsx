"use client";

import React, { useEffect, useState } from "react";
import {
  fetchMaintenanceInfo,
  fetchMaintenanceAnalytics,
  fetchAnomalies,
  fetchPredictions,
  fetchMaintenanceSchedules,
  acknowledgeAnomaly,
  type MaintenanceInfo,
  type MaintenanceAnalytics,
  type AnomalyDetection,
  type FailurePrediction,
  type MaintenanceSchedule,
  type AnomalySeverity,
  type MaintenanceStatus,
} from "@/lib/maintenanceApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function MaintenancePage() {
  const [info, setInfo] = useState<LoadState<MaintenanceInfo>>({ loading: true });
  const [analytics, setAnalytics] = useState<LoadState<MaintenanceAnalytics>>({ loading: true });
  const [anomalies, setAnomalies] = useState<LoadState<AnomalyDetection[]>>({ loading: true });
  const [predictions, setPredictions] = useState<LoadState<FailurePrediction[]>>({ loading: true });
  const [schedules, setSchedules] = useState<LoadState<MaintenanceSchedule[]>>({ loading: true });

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    // Fetch module info
    fetchMaintenanceInfo()
      .then((d) => setInfo({ data: d, loading: false }))
      .catch((e) => setInfo({ loading: false, error: String(e) }));

    // Fetch analytics
    fetchMaintenanceAnalytics()
      .then((d) => setAnalytics({ data: d, loading: false }))
      .catch((e) => setAnalytics({ loading: false, error: String(e) }));

    // Fetch anomalies (unacknowledged only)
    fetchAnomalies({ acknowledged: false })
      .then((d) => setAnomalies({ data: d, loading: false }))
      .catch((e) => setAnomalies({ loading: false, error: String(e) }));

    // Fetch predictions (probability > 50%)
    fetchPredictions({ min_probability: 0.5 })
      .then((d) => setPredictions({ data: d, loading: false }))
      .catch((e) => setPredictions({ loading: false, error: String(e) }));

    // Fetch schedules
    fetchMaintenanceSchedules()
      .then((d) => setSchedules({ data: d, loading: false }))
      .catch((e) => setSchedules({ loading: false, error: String(e) }));
  }, [refreshKey]);

  const handleAcknowledge = async (anomalyId: string) => {
    try {
      await acknowledgeAnomaly(anomalyId);
      setRefreshKey((k) => k + 1); // Refresh data
    } catch (error) {
      console.error("Failed to acknowledge anomaly:", error);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">Predictive Maintenance</h1>
        <p className="text-sm text-neutral-400">
          Fleet health monitoring, anomaly detection, and failure prediction for proactive maintenance.
        </p>
      </header>

      {/* Fleet Summary Cards */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <SummaryCard
          title="Fleet Health"
          value={analytics.data ? `${analytics.data.average_fleet_health.toFixed(1)}%` : "—"}
          subtitle={analytics.data ? `${analytics.data.total_robots} robots, ${analytics.data.total_components} components` : ""}
          loading={analytics.loading}
          color="emerald"
        />
        <SummaryCard
          title="Active Anomalies"
          value={analytics.data?.active_anomalies.toString() ?? "—"}
          subtitle={anomalies.data ? `${anomalies.data.filter(a => a.severity === "critical").length} critical` : ""}
          loading={analytics.loading}
          color={analytics.data && analytics.data.active_anomalies > 0 ? "amber" : "emerald"}
        />
        <SummaryCard
          title="Pending Predictions"
          value={analytics.data?.pending_predictions.toString() ?? "—"}
          subtitle="Failure predictions"
          loading={analytics.loading}
          color={analytics.data && analytics.data.pending_predictions > 0 ? "red" : "emerald"}
        />
        <SummaryCard
          title="Uptime"
          value={analytics.data ? `${analytics.data.uptime_percentage.toFixed(1)}%` : "—"}
          subtitle={analytics.data ? `${analytics.data.scheduled_maintenance_count} scheduled, ${analytics.data.overdue_maintenance_count} overdue` : ""}
          loading={analytics.loading}
          color="sky"
        />
      </section>

      {/* Component Health Grid */}
      {analytics.data && analytics.data.health_summaries.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-neutral-300">Component Health Summary</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {analytics.data.health_summaries.map((summary) => (
              <ComponentHealthCard key={summary.component_type} summary={summary} />
            ))}
          </div>
        </section>
      )}

      {/* Main Content Grid */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Active Anomalies */}
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Active Anomalies</h2>
            <span className="rounded-full bg-amber-900/60 px-2 py-1 text-[10px] text-amber-300">
              {anomalies.data?.length ?? 0} unacknowledged
            </span>
          </div>

          {anomalies.loading && (
            <div className="text-xs text-neutral-400">Loading anomalies...</div>
          )}

          {anomalies.error && (
            <div className="text-xs text-red-400">{anomalies.error}</div>
          )}

          {!anomalies.loading && anomalies.data && anomalies.data.length === 0 && (
            <div className="text-xs text-neutral-500">No active anomalies detected.</div>
          )}

          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {anomalies.data?.map((anomaly) => (
              <AnomalyCard key={anomaly.anomaly_id} anomaly={anomaly} onAcknowledge={handleAcknowledge} />
            ))}
          </div>
        </div>

        {/* Failure Predictions */}
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Failure Predictions</h2>
            <span className="rounded-full bg-red-900/60 px-2 py-1 text-[10px] text-red-300">
              {predictions.data?.length ?? 0} active
            </span>
          </div>

          {predictions.loading && (
            <div className="text-xs text-neutral-400">Loading predictions...</div>
          )}

          {predictions.error && (
            <div className="text-xs text-red-400">{predictions.error}</div>
          )}

          {!predictions.loading && predictions.data && predictions.data.length === 0 && (
            <div className="text-xs text-neutral-500">No failure predictions at this time.</div>
          )}

          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {predictions.data?.map((prediction) => (
              <PredictionCard key={prediction.prediction_id} prediction={prediction} />
            ))}
          </div>
        </div>
      </section>

      {/* Maintenance Schedule */}
      <section>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Maintenance Schedule</h2>
            <span className="text-[10px] text-neutral-500">
              {schedules.data?.length ?? 0} tasks
            </span>
          </div>

          {schedules.loading && (
            <div className="text-xs text-neutral-400">Loading schedules...</div>
          )}

          {schedules.error && (
            <div className="text-xs text-red-400">{schedules.error}</div>
          )}

          {!schedules.loading && schedules.data && schedules.data.length === 0 && (
            <div className="text-xs text-neutral-500">No scheduled maintenance tasks.</div>
          )}

          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {schedules.data?.map((schedule) => (
              <MaintenanceCard key={schedule.schedule_id} schedule={schedule} />
            ))}
          </div>
        </div>
      </section>

      {/* Module Info */}
      {info.data && (
        <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
          <div className="text-xs text-neutral-400">
            <span className="font-semibold text-neutral-300">{info.data.module}</span> v{info.data.version} •{" "}
            {info.data.description}
          </div>
        </section>
      )}
    </div>
  );
}

// ========== Components ==========

type SummaryCardProps = {
  title: string;
  value: string;
  subtitle?: string;
  loading?: boolean;
  color?: "emerald" | "amber" | "red" | "sky";
};

function SummaryCard({ title, value, subtitle, loading, color = "emerald" }: SummaryCardProps) {
  const colorClasses = {
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    red: "text-red-400",
    sky: "text-sky-400",
  };

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="flex flex-col gap-1">
        <span className="text-xs font-semibold text-neutral-300">{title}</span>
        {loading ? (
          <span className="text-sm text-neutral-400">Loading...</span>
        ) : (
          <>
            <span className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</span>
            {subtitle && <span className="text-[11px] text-neutral-500">{subtitle}</span>}
          </>
        )}
      </div>
    </div>
  );
}

function ComponentHealthCard({ summary }: { summary: any }) {
  const healthPercent = summary.average_health_score;
  const healthColor =
    healthPercent >= 80
      ? "text-emerald-400"
      : healthPercent >= 60
        ? "text-amber-400"
        : "text-red-400";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-neutral-200">
            {summary.component_type.toUpperCase()}
          </span>
          <span className="text-[10px] text-neutral-500">{summary.total_components} components</span>
        </div>
        <span className={`text-lg font-bold ${healthColor}`}>{healthPercent.toFixed(0)}%</span>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-1 text-[10px]">
        <div className="flex flex-col">
          <span className="text-emerald-400">{summary.healthy_components}</span>
          <span className="text-neutral-500">Healthy</span>
        </div>
        <div className="flex flex-col">
          <span className="text-amber-400">{summary.degraded_components}</span>
          <span className="text-neutral-500">Degraded</span>
        </div>
        <div className="flex flex-col">
          <span className="text-red-400">{summary.critical_components}</span>
          <span className="text-neutral-500">Critical</span>
        </div>
      </div>
    </div>
  );
}

function AnomalyCard({
  anomaly,
  onAcknowledge,
}: {
  anomaly: AnomalyDetection;
  onAcknowledge: (id: string) => void;
}) {
  const severityColors: Record<AnomalySeverity, string> = {
    low: "bg-neutral-700 text-neutral-300",
    medium: "bg-amber-900/60 text-amber-300",
    high: "bg-orange-900/60 text-orange-300",
    critical: "bg-red-900/60 text-red-300",
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-[9px] font-medium uppercase ${severityColors[anomaly.severity]}`}
            >
              {anomaly.severity}
            </span>
            <span className="text-[10px] text-neutral-500">{anomaly.anomaly_type}</span>
          </div>
          <span className="text-xs text-neutral-200">{anomaly.description}</span>
          <span className="text-[10px] text-neutral-500">
            Robot: {anomaly.robot_id} • Component: {anomaly.component_id}
          </span>
          {anomaly.recommended_action && (
            <span className="text-[10px] text-sky-400">→ {anomaly.recommended_action}</span>
          )}
        </div>
        <button
          onClick={() => onAcknowledge(anomaly.anomaly_id)}
          className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1 text-[10px] text-neutral-300 hover:border-emerald-500"
        >
          Ack
        </button>
      </div>
    </div>
  );
}

function PredictionCard({ prediction }: { prediction: FailurePrediction }) {
  const risk = prediction.failure_probability;
  const riskColor = risk >= 0.8 ? "text-red-400" : risk >= 0.6 ? "text-orange-400" : "text-amber-400";

  const timeToFailure = prediction.time_to_failure_hours;
  const timeDisplay = timeToFailure
    ? timeToFailure < 24
      ? `${timeToFailure.toFixed(1)}h`
      : `${(timeToFailure / 24).toFixed(1)}d`
    : "Unknown";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className={`text-lg font-bold ${riskColor}`}>{(risk * 100).toFixed(0)}%</span>
            <span className="text-[10px] text-neutral-500">failure risk</span>
          </div>
          <span className="text-xs text-neutral-200">
            {prediction.component_type.toUpperCase()} ({prediction.component_id})
          </span>
          <span className="text-[10px] text-neutral-500">Robot: {prediction.robot_id}</span>
          {timeToFailure && (
            <span className="text-[10px] text-amber-400">Est. failure in {timeDisplay}</span>
          )}
          {prediction.root_cause && (
            <span className="text-[10px] text-neutral-400">Cause: {prediction.root_cause}</span>
          )}
        </div>
      </div>
      {prediction.recommended_actions.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {prediction.recommended_actions.slice(0, 2).map((action, i) => (
            <span key={i} className="text-[9px] text-sky-400">
              • {action}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MaintenanceCard({ schedule }: { schedule: MaintenanceSchedule }) {
  const statusColors: Record<MaintenanceStatus, string> = {
    scheduled: "bg-sky-900/60 text-sky-300",
    in_progress: "bg-amber-900/60 text-amber-300",
    completed: "bg-emerald-900/60 text-emerald-300",
    cancelled: "bg-neutral-900/80 text-neutral-400",
    overdue: "bg-red-900/60 text-red-300",
  };

  const scheduledDate = new Date(schedule.scheduled_time * 1000);
  const isOverdue = schedule.status === "overdue";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-[9px] font-medium uppercase ${statusColors[schedule.status]}`}
            >
              {schedule.status}
            </span>
            <span className={`text-[10px] font-semibold ${isOverdue ? "text-red-400" : "text-neutral-300"}`}>
              Priority {schedule.priority}
            </span>
          </div>
          <span className="text-xs text-neutral-200">{schedule.description}</span>
          <span className="text-[10px] text-neutral-500">
            {schedule.maintenance_type} • {schedule.estimated_duration_hours}h • Robot: {schedule.robot_id}
          </span>
          <span className="text-[10px] text-neutral-500">
            {isOverdue ? "Overdue: " : "Scheduled: "}{scheduledDate.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}
