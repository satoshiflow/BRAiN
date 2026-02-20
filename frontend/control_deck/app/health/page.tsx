"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useEffect, useState } from "react";
import {
  fetchSystemHealth,
  fetchRuntimeMetrics,
  fetchProtectionStatus,
  startRuntimeAuditor,
  type SystemHealth,
  type RuntimeMetrics,
  type ProtectionStatus,
  type HealthStatus as HealthStatusType,
} from "@/lib/systemHealthApi";

// =============================================================================
// STATUS BADGE
// =============================================================================

const StatusBadge: React.FC<{ status: HealthStatusType }> = ({ status }) => {
  const colors = {
    healthy: "bg-green-500/20 text-green-400 border-green-500/30",
    degraded: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    critical: "bg-red-500/20 text-red-400 border-red-500/30",
    unknown: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  };

  const icons = {
    healthy: "✓",
    degraded: "⚠",
    critical: "✗",
    unknown: "?",
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${colors[status]}`}>
      <span className="text-lg">{icons[status]}</span>
      <span className="font-medium uppercase text-sm">{status}</span>
    </div>
  );
};

// =============================================================================
// EDGE OF CHAOS INDICATOR
// =============================================================================

const EdgeOfChaosIndicator: React.FC<{ score?: number; assessment?: string }> = ({ score, assessment }) => {
  if (score === undefined || score === null) {
    return (
      <div className="text-gray-500 text-sm">No data</div>
    );
  }

  const getColor = () => {
    if (score < 0.3) return "text-blue-400";
    if (score > 0.8) return "text-red-400";
    return "text-green-400";
  };

  const getAssessmentText = () => {
    if (assessment === "too_ordered") return "Too Ordered";
    if (assessment === "too_chaotic") return "Too Chaotic";
    return "Optimal";
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full ${getColor()} bg-current transition-all`}
            style={{ width: `${score * 100}%` }}
          />
        </div>
        <div className={`font-mono text-lg ${getColor()}`}>
          {score.toFixed(2)}
        </div>
      </div>
      <div className="text-sm text-gray-400">
        {getAssessmentText()} (optimal: 0.5-0.7)
      </div>
    </div>
  );
};

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function HealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [runtimeMetrics, setRuntimeMetrics] = useState<RuntimeMetrics | null>(null);
  const [protectionStatus, setProtectionStatus] = useState<ProtectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadData = async () => {
    try {
      const [healthData, metricsData, protectionData] = await Promise.all([
        fetchSystemHealth(),
        fetchRuntimeMetrics().catch(() => null),
        fetchProtectionStatus().catch(() => null),
      ]);

      setHealth(healthData);
      setRuntimeMetrics(metricsData);
      setProtectionStatus(protectionData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load health data");
    } finally {
      setLoading(false);
    }
  };

  const handleStartAuditor = async () => {
    try {
      await startRuntimeAuditor();
      await loadData();
    } catch (err) {
      console.error("Failed to start runtime auditor:", err);
    }
  };

  useEffect(() => {
    loadData();

    if (autoRefresh) {
      const interval = setInterval(loadData, 30000); // Refresh every 30s
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <div className="text-xl text-gray-400">Loading health data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <div className="text-xl text-red-400">Error: {error}</div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <div className="text-xl text-gray-400">No health data available</div>
      </div>
    );
  }

  const edgeOfChaosScore = health.audit_metrics?.edge_of_chaos_score ?? runtimeMetrics?.edge_of_chaos?.score;
  const edgeOfChaosAssessment = runtimeMetrics?.edge_of_chaos?.assessment;

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* HEADER */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">System Health & Audit</h1>
            <p className="text-gray-400 mt-1">
              Comprehensive monitoring and diagnostics
            </p>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded ${
                autoRefresh ? "bg-blue-600" : "bg-gray-700"
              } hover:opacity-80`}
            >
              Auto-refresh: {autoRefresh ? "ON" : "OFF"}
            </button>
            <button
              onClick={loadData}
              className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600"
            >
              Refresh Now
            </button>
          </div>
        </div>

        {/* OVERALL STATUS */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold mb-2">Overall Status</h2>
              <p className="text-gray-400 text-sm">
                Last updated: {new Date(health.timestamp).toLocaleString()}
              </p>
            </div>
            <StatusBadge status={health.overall_status} />
          </div>

          {health.uptime_seconds && (
            <div className="mt-4 text-sm text-gray-400">
              Uptime: {Math.floor(health.uptime_seconds / 3600)}h{" "}
              {Math.floor((health.uptime_seconds % 3600) / 60)}m
            </div>
          )}
        </div>

        {/* EDGE OF CHAOS */}
        {edgeOfChaosScore !== undefined && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Edge-of-Chaos Score</h2>
            <EdgeOfChaosIndicator score={edgeOfChaosScore} assessment={edgeOfChaosAssessment} />
          </div>
        )}

        {/* SUB-SYSTEMS HEALTH */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Immune System */}
          {health.immune_health && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-sm text-gray-400">Immune System</h3>
              <div className="text-2xl font-bold">
                {health.immune_health.active_issues}
              </div>
              <div className="text-sm text-gray-500">Active Issues</div>
              {health.immune_health.critical_issues > 0 && (
                <div className="mt-2 text-red-400 text-sm">
                  {health.immune_health.critical_issues} Critical
                </div>
              )}
            </div>
          )}

          {/* Threats */}
          {health.threats_health && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-sm text-gray-400">Threats</h3>
              <div className="text-2xl font-bold">
                {health.threats_health.active_threats}
              </div>
              <div className="text-sm text-gray-500">Active Threats</div>
            </div>
          )}

          {/* Missions */}
          {health.mission_health && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-sm text-gray-400">Mission Queue</h3>
              <div className="text-2xl font-bold">
                {health.mission_health.queue_depth}
              </div>
              <div className="text-sm text-gray-500">Queue Depth</div>
            </div>
          )}

          {/* Agents */}
          {health.agent_health && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-sm text-gray-400">Agents</h3>
              <div className="text-2xl font-bold">
                {health.agent_health.active_agents}/{health.agent_health.total_agents}
              </div>
              <div className="text-sm text-gray-500">Active/Total</div>
            </div>
          )}
        </div>

        {/* SELF-PROTECTION STATUS */}
        {protectionStatus && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Self-Protection Status</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-400 mb-1">Backpressure</div>
                <div className={`font-semibold ${protectionStatus.backpressure_enabled ? "text-yellow-400" : "text-green-400"}`}>
                  {protectionStatus.backpressure_enabled ? "ENABLED" : "Disabled"}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400 mb-1">Circuit Breaker</div>
                <div className={`font-semibold ${protectionStatus.circuit_breaker_open ? "text-red-400" : "text-green-400"}`}>
                  {protectionStatus.circuit_breaker_open ? "OPEN" : "Closed"}
                </div>
              </div>
            </div>
            {protectionStatus.protection_actions_count > 0 && (
              <div className="mt-4 text-sm text-gray-400">
                Protection actions triggered: {protectionStatus.protection_actions_count}
              </div>
            )}
          </div>
        )}

        {/* BOTTLENECKS */}
        {health.bottlenecks.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Identified Bottlenecks</h2>
            <div className="space-y-3">
              {health.bottlenecks.map((bottleneck, idx) => (
                <div key={idx} className="border-l-4 border-yellow-500 pl-4 py-2">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold">{bottleneck.component}</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      bottleneck.severity === "critical" ? "bg-red-500/20 text-red-400" :
                      bottleneck.severity === "high" ? "bg-orange-500/20 text-orange-400" :
                      bottleneck.severity === "medium" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-blue-500/20 text-blue-400"
                    }`}>
                      {bottleneck.severity.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400">{bottleneck.description}</div>
                  <div className="text-sm text-gray-500 mt-1">
                    <strong>Recommendation:</strong> {bottleneck.recommendation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RECOMMENDATIONS */}
        {health.recommendations.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Optimization Recommendations</h2>
            <div className="space-y-3">
              {health.recommendations.map((rec, idx) => (
                <div key={idx} className="bg-slate-800 rounded p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      rec.priority === "CRITICAL" ? "bg-red-500/20 text-red-400" :
                      rec.priority === "HIGH" ? "bg-orange-500/20 text-orange-400" :
                      rec.priority === "MEDIUM" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-blue-500/20 text-blue-400"
                    }`}>
                      {rec.priority}
                    </span>
                    <span className="font-semibold">{rec.title}</span>
                  </div>
                  <div className="text-sm text-gray-400">{rec.description}</div>
                  {rec.impact && (
                    <div className="text-sm text-gray-500 mt-2">
                      <strong>Impact:</strong> {rec.impact}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ANOMALIES */}
        {runtimeMetrics && runtimeMetrics.anomalies.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Detected Anomalies</h2>
            <div className="space-y-3">
              {runtimeMetrics.anomalies.map((anomaly, idx) => (
                <div key={idx} className="border-l-4 border-red-500 pl-4 py-2">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold">{anomaly.type}</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      anomaly.severity === "critical" ? "bg-red-500/20 text-red-400" :
                      anomaly.severity === "high" ? "bg-orange-500/20 text-orange-400" :
                      "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {anomaly.severity.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400">{anomaly.description}</div>
                  {anomaly.recommendation && (
                    <div className="text-sm text-gray-500 mt-1">
                      <strong>Recommendation:</strong> {anomaly.recommendation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
