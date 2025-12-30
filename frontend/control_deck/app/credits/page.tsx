"use client";

import { useState, useEffect } from "react";

/**
 * Credits System Dashboard
 * Phase 8b: UI for complete credit system (Phase 5-7 components)
 *
 * Tabs:
 * 1. Overview - System statistics and health
 * 2. Ledger - Transaction history and integrity
 * 3. Edge-of-Chaos - Controller status and regulation
 * 4. Evolution - Trends and recommendations
 * 5. Synergie - Collaboration and reuse
 * 6. Approval Gates - Human oversight
 * 7. Resource Pools - Knowledge sharing
 * 8. Agent Ratings - Performance metrics
 */

interface CreditStats {
  total_credits_allocated: number;
  total_credits_consumed: number;
  total_credits_available: number;
  total_entities: number;
  total_agents: number;
  total_missions: number;
  ledger_entries: number;
  ledger_integrity_valid: boolean;
}

interface LedgerEntry {
  id: string;
  timestamp: string;
  transaction_type: string;
  entity_id: string;
  entity_type: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  reason: string;
}

interface EoCStatus {
  current_score: number;
  status: string;
  regen_multiplier: number;
  actions: string[];
  reasoning: string;
  last_regulated_at: string;
}

interface EvolutionAnalysis {
  analyzed_at: string;
  trends: Array<{
    metric_name: string;
    current_value: number;
    direction: string;
    is_significant: boolean;
  }>;
  recommendations: Array<{
    recommendation_id: string;
    recommendation_type: string;
    priority: number;
    title: string;
    description: string;
    requires_human_approval: boolean;
  }>;
  overall_health: string;
}

interface SynergieStats {
  total_reuse_detections: number;
  total_refund_amount: number;
  total_collaboration_events: number;
  unique_agents: number;
  average_similarity: number;
  average_value_added: number;
}

interface ApprovalRequest {
  request_id: string;
  action_type: string;
  action_description: string;
  severity: string;
  status: string;
  created_at: string;
  expires_at: string;
  approvals_received: number;
  approvals_required: number;
  is_pending: boolean;
}

type TabType = "overview" | "ledger" | "eoc" | "evolution" | "synergie" | "approval" | "resources" | "ratings";

export default function CreditsPage() {
  const [selectedTab, setSelectedTab] = useState<TabType>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State for each tab
  const [stats, setStats] = useState<CreditStats | null>(null);
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [eocStatus, setEocStatus] = useState<EoCStatus | null>(null);
  const [evolution, setEvolution] = useState<EvolutionAnalysis | null>(null);
  const [synergieStats, setSynergieStats] = useState<SynergieStats | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, [selectedTab]);

  const fetchData = async () => {
    try {
      setLoading(true);

      switch (selectedTab) {
        case "overview":
          await fetchStats();
          break;
        case "ledger":
          await fetchLedger();
          break;
        case "eoc":
          await fetchEoC();
          break;
        case "evolution":
          await fetchEvolution();
          break;
        case "synergie":
          await fetchSynergie();
          break;
        case "approval":
          await fetchApprovals();
          break;
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    const response = await fetch("http://localhost:8000/api/credits/ledger/statistics");
    if (!response.ok) throw new Error("Failed to fetch statistics");
    const data = await response.json();
    setStats(data);
  };

  const fetchLedger = async () => {
    const response = await fetch("http://localhost:8000/api/credits/history?limit=50");
    if (!response.ok) throw new Error("Failed to fetch ledger");
    const data = await response.json();
    setLedgerEntries(data.entries || []);
  };

  const fetchEoC = async () => {
    const response = await fetch("http://localhost:8000/api/credits/eoc/status");
    if (!response.ok) throw new Error("Failed to fetch EoC status");
    const data = await response.json();
    setEocStatus(data);
  };

  const fetchEvolution = async () => {
    // For now, we'll need to trigger analysis
    // In production, this would be periodic background analysis
    const response = await fetch("http://localhost:8000/api/credits/evolution/recommendations");
    if (!response.ok) throw new Error("Failed to fetch evolution data");
    const data = await response.json();
    setEvolution(data);
  };

  const fetchSynergie = async () => {
    const response = await fetch("http://localhost:8000/api/credits/synergie/statistics");
    if (!response.ok) throw new Error("Failed to fetch synergie statistics");
    const data = await response.json();
    setSynergieStats(data);
  };

  const fetchApprovals = async () => {
    const response = await fetch("http://localhost:8000/api/credits/approval/pending");
    if (!response.ok) throw new Error("Failed to fetch approvals");
    const data = await response.json();
    setApprovals(data);
  };

  const handleApprove = async (requestId: string, justification: string) => {
    const response = await fetch("http://localhost:8000/api/credits/approval/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        approver_id: "admin", // TODO: Get from auth
        justification,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      alert(`Approval failed: ${error.detail}`);
      return;
    }

    alert("Approval successful!");
    fetchApprovals();
  };

  const handleReject = async (requestId: string, reason: string) => {
    const response = await fetch("http://localhost:8000/api/credits/approval/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        approver_id: "admin", // TODO: Get from auth
        reason,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      alert(`Rejection failed: ${error.detail}`);
      return;
    }

    alert("Rejection successful!");
    fetchApprovals();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Credits System Dashboard</h1>
        <p className="text-gray-600">
          Myzel-Hybrid-Charta: Cooperation-based resource allocation
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b overflow-x-auto">
        {[
          { key: "overview", label: "📊 Overview" },
          { key: "ledger", label: "📜 Ledger" },
          { key: "eoc", label: "⚡ Edge-of-Chaos" },
          { key: "evolution", label: "📈 Evolution" },
          { key: "synergie", label: "🤝 Synergie" },
          { key: "approval", label: "✋ Approvals" },
          { key: "resources", label: "📚 Resources" },
          { key: "ratings", label: "⭐ Ratings" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSelectedTab(tab.key as TabType)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
              selectedTab === tab.key
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">⚠️ Error: {error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      )}

      {/* Tab Content */}
      {!loading && (
        <>
          {/* Overview Tab */}
          {selectedTab === "overview" && stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  title="Total Allocated"
                  value={stats.total_credits_allocated.toFixed(2)}
                  subtitle="credits"
                  color="blue"
                />
                <StatCard
                  title="Total Consumed"
                  value={stats.total_credits_consumed.toFixed(2)}
                  subtitle="credits"
                  color="purple"
                />
                <StatCard
                  title="Available"
                  value={stats.total_credits_available.toFixed(2)}
                  subtitle="credits"
                  color="green"
                />
                <StatCard
                  title="Ledger Entries"
                  value={stats.ledger_entries.toString()}
                  subtitle={stats.ledger_integrity_valid ? "✓ Valid" : "⚠ Invalid"}
                  color={stats.ledger_integrity_valid ? "green" : "red"}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                  title="Total Entities"
                  value={stats.total_entities.toString()}
                  subtitle="entities"
                  color="gray"
                />
                <StatCard
                  title="Agents"
                  value={stats.total_agents.toString()}
                  subtitle="agents"
                  color="gray"
                />
                <StatCard
                  title="Missions"
                  value={stats.total_missions.toString()}
                  subtitle="missions"
                  color="gray"
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">System Health</h3>
                <p className="text-gray-700">
                  Ledger Integrity: {stats.ledger_integrity_valid ? "✅ Valid" : "❌ Invalid"}
                </p>
                <p className="text-gray-700 mt-2">
                  Allocation Rate:{" "}
                  {((stats.total_credits_consumed / stats.total_credits_allocated) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          )}

          {/* Ledger Tab */}
          {selectedTab === "ledger" && (
            <div className="space-y-4">
              {ledgerEntries.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                  <p className="text-gray-600">No ledger entries</p>
                </div>
              ) : (
                ledgerEntries.map((entry) => (
                  <div
                    key={entry.id}
                    className="bg-white border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300">
                            {entry.transaction_type.toUpperCase()}
                          </span>
                          <span className="text-sm text-gray-600">{entry.entity_id}</span>
                        </div>
                        <p className="text-gray-700">{entry.reason}</p>
                      </div>
                      <div className="text-right">
                        <p className={`text-lg font-bold ${entry.amount >= 0 ? "text-green-600" : "text-red-600"}`}>
                          {entry.amount >= 0 ? "+" : ""}
                          {entry.amount.toFixed(2)}
                        </p>
                        <p className="text-sm text-gray-600">Balance: {entry.balance_after.toFixed(2)}</p>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t text-xs text-gray-500">
                      {new Date(entry.timestamp).toLocaleString()} • ID: {entry.id.substring(0, 12)}...
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Edge-of-Chaos Tab */}
          {selectedTab === "eoc" && eocStatus && (
            <div className="space-y-6">
              <div className="bg-white border rounded-lg p-6 shadow-sm">
                <h3 className="text-xl font-bold mb-4">Edge-of-Chaos Controller</h3>

                {/* EoC Score Gauge */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Current Score</span>
                    <span className="text-2xl font-bold text-blue-600">
                      {eocStatus.current_score.toFixed(3)}
                    </span>
                  </div>
                  <div className="relative h-4 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`absolute h-full ${
                        eocStatus.current_score >= 0.5 && eocStatus.current_score <= 0.7
                          ? "bg-green-500"
                          : eocStatus.current_score < 0.5
                          ? "bg-blue-500"
                          : "bg-red-500"
                      }`}
                      style={{ width: `${eocStatus.current_score * 100}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-1 text-xs text-gray-600">
                    <span>0.0 (Ordered)</span>
                    <span className="font-semibold">0.5-0.7 (Optimal)</span>
                    <span>1.0 (Chaos)</span>
                  </div>
                </div>

                {/* Status */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-600">Status</p>
                    <p
                      className={`text-lg font-semibold ${
                        eocStatus.status === "optimal" ? "text-green-600" : "text-orange-600"
                      }`}
                    >
                      {eocStatus.status.toUpperCase()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Regen Multiplier</p>
                    <p className="text-lg font-semibold">{eocStatus.regen_multiplier.toFixed(2)}x</p>
                  </div>
                </div>

                {/* Actions */}
                {eocStatus.actions.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Active Actions:</p>
                    <div className="flex flex-wrap gap-2">
                      {eocStatus.actions.map((action, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-300"
                        >
                          {action}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reasoning */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm font-medium text-gray-700 mb-1">Reasoning:</p>
                  <p className="text-gray-800">{eocStatus.reasoning}</p>
                </div>

                <p className="text-xs text-gray-500 mt-4">
                  Last regulated: {new Date(eocStatus.last_regulated_at).toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {/* Evolution Tab */}
          {selectedTab === "evolution" && evolution && (
            <div className="space-y-6">
              {/* Overall Health */}
              <div className="bg-white border rounded-lg p-6 shadow-sm">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold">System Health</h3>
                  <span
                    className={`px-4 py-2 rounded-full text-sm font-semibold ${
                      evolution.overall_health === "healthy"
                        ? "bg-green-100 text-green-800 border border-green-300"
                        : evolution.overall_health === "degraded"
                        ? "bg-orange-100 text-orange-800 border border-orange-300"
                        : "bg-gray-100 text-gray-800 border border-gray-300"
                    }`}
                  >
                    {evolution.overall_health.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Trends */}
              {evolution.trends && evolution.trends.length > 0 && (
                <div className="bg-white border rounded-lg p-6 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4">System Trends</h3>
                  <div className="space-y-3">
                    {evolution.trends.map((trend, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex-1">
                          <p className="font-medium">{trend.metric_name.replace("_", " ").toUpperCase()}</p>
                          <p className="text-sm text-gray-600">
                            Current: {trend.current_value.toFixed(2)}
                            {trend.is_significant && (
                              <span className="ml-2 text-xs text-orange-600 font-semibold">SIGNIFICANT</span>
                            )}
                          </p>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            trend.direction === "improving"
                              ? "bg-green-100 text-green-800"
                              : trend.direction === "declining"
                              ? "bg-red-100 text-red-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {trend.direction === "improving" ? "↗" : trend.direction === "declining" ? "↘" : "→"}{" "}
                          {trend.direction.toUpperCase()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {evolution.recommendations && evolution.recommendations.length > 0 && (
                <div className="bg-white border rounded-lg p-6 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4">Growth Recommendations</h3>
                  <div className="space-y-4">
                    {evolution.recommendations.map((rec) => (
                      <div key={rec.recommendation_id} className="border rounded-lg p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="px-2 py-1 rounded text-xs font-bold bg-purple-100 text-purple-800">
                                Priority: {rec.priority}
                              </span>
                              {rec.requires_human_approval && (
                                <span className="px-2 py-1 rounded text-xs font-bold bg-orange-100 text-orange-800">
                                  ✋ APPROVAL REQUIRED
                                </span>
                              )}
                            </div>
                            <h4 className="font-semibold text-lg">{rec.title}</h4>
                          </div>
                        </div>
                        <p className="text-gray-700 mt-2">{rec.description}</p>
                        <p className="text-xs text-gray-500 mt-2">
                          Type: {rec.recommendation_type.replace("_", " ")}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Synergie Tab */}
          {selectedTab === "synergie" && synergieStats && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <StatCard
                  title="Reuse Detections"
                  value={synergieStats.total_reuse_detections.toString()}
                  subtitle="detected"
                  color="blue"
                />
                <StatCard
                  title="Total Refunds"
                  value={synergieStats.total_refund_amount.toFixed(2)}
                  subtitle="credits saved"
                  color="green"
                />
                <StatCard
                  title="Collaborations"
                  value={synergieStats.total_collaboration_events.toString()}
                  subtitle="events"
                  color="purple"
                />
              </div>

              <div className="bg-white border rounded-lg p-6 shadow-sm">
                <h3 className="text-lg font-semibold mb-4">Cooperation Metrics</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Unique Collaborating Agents</span>
                    <span className="font-bold text-xl">{synergieStats.unique_agents}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Average Similarity Score</span>
                    <span className="font-bold text-xl">
                      {(synergieStats.average_similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700">Average Value Added</span>
                    <span className="font-bold text-xl">
                      {(synergieStats.average_value_added * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2 text-green-800">🤝 Myzel-Hybrid Principle</h3>
                <p className="text-gray-700">
                  Cooperation over competition: {synergieStats.total_refund_amount.toFixed(2)} credits saved through
                  work reuse and {synergieStats.total_collaboration_events} collaboration events.
                </p>
              </div>
            </div>
          )}

          {/* Approval Tab */}
          {selectedTab === "approval" && (
            <div className="space-y-4">
              {approvals.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                  <p className="text-gray-600">No pending approvals</p>
                </div>
              ) : (
                approvals.map((approval) => (
                  <div
                    key={approval.request_id}
                    className="bg-white border rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                              approval.severity === "critical"
                                ? "bg-red-100 text-red-800 border-red-300"
                                : approval.severity === "high"
                                ? "bg-orange-100 text-orange-800 border-orange-300"
                                : approval.severity === "medium"
                                ? "bg-yellow-100 text-yellow-800 border-yellow-300"
                                : "bg-green-100 text-green-800 border-green-300"
                            }`}
                          >
                            {approval.severity.toUpperCase()}
                          </span>
                          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300">
                            {approval.action_type.replace("_", " ").toUpperCase()}
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold">{approval.action_description}</h3>
                      </div>

                      {approval.is_pending && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              const justification = prompt("Justification (required for HIGH/CRITICAL):");
                              if (justification) handleApprove(approval.request_id, justification);
                            }}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                          >
                            ✓ Approve
                          </button>
                          <button
                            onClick={() => {
                              const reason = prompt("Rejection reason (required):");
                              if (reason) handleReject(approval.request_id, reason);
                            }}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                          >
                            ✗ Reject
                          </button>
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-600">Created</p>
                        <p className="font-medium">{new Date(approval.created_at).toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Expires</p>
                        <p className="font-medium">{new Date(approval.expires_at).toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Approvals</p>
                        <p className="font-medium">
                          {approval.approvals_received}/{approval.approvals_required}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 pt-4 border-t">
                      <p className="text-xs text-gray-500">ID: {approval.request_id}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Resources Tab */}
          {selectedTab === "resources" && (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <p className="text-gray-600">Resource Pools browser coming soon...</p>
              <p className="text-sm text-gray-500 mt-2">Search, contribute, and access shared knowledge & code</p>
            </div>
          )}

          {/* Ratings Tab */}
          {selectedTab === "ratings" && (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <p className="text-gray-600">Agent Ratings dashboard coming soon...</p>
              <p className="text-sm text-gray-500 mt-2">Agent performance metrics and mission matching</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Reusable Stat Card Component
function StatCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string;
  value: string;
  subtitle: string;
  color: string;
}) {
  const colorClasses = {
    blue: "border-blue-200 bg-blue-50",
    purple: "border-purple-200 bg-purple-50",
    green: "border-green-200 bg-green-50",
    red: "border-red-200 bg-red-50",
    gray: "border-gray-200 bg-gray-50",
  };

  return (
    <div className={`border rounded-lg p-4 ${colorClasses[color as keyof typeof colorClasses] || colorClasses.gray}`}>
      <p className="text-sm text-gray-600 mb-1">{title}</p>
      <p className="text-2xl font-bold mb-1">{value}</p>
      <p className="text-xs text-gray-600">{subtitle}</p>
    </div>
  );
}
