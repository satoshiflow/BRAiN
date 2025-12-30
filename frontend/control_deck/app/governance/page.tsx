"use client";

import { useState, useEffect } from "react";
import { useCurrentUser } from "@/hooks/useAuth";

/**
 * Governance & HITL Approvals Dashboard
 * Sprint 16: Human-in-the-loop approval workflows
 */

interface ApprovalSummary {
  approval_id: string;
  approval_type: string;
  status: string;
  risk_tier: string;
  requested_by: string;
  requested_at: number;
  expires_at: number;
  time_until_expiry: number;
  action_description: string;
}

export default function GovernancePage() {
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<"pending" | "approved" | "rejected" | "expired">("pending");

  // Get current user for audit trail
  const { data: currentUser } = useCurrentUser();

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [selectedTab]);

  const fetchApprovals = async () => {
    try {
      const endpoint = `/api/governance/approvals/${selectedTab}`;
      const response = await fetch(`http://localhost:8000${endpoint}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch approvals: ${response.statusText}`);
      }

      const data = await response.json();
      setPendingApprovals(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approvalId: string) => {
    if (!confirm("Are you sure you want to approve this request?")) {
      return;
    }

    // Ensure user is authenticated
    const actorId = currentUser?.username || "anonymous";

    try {
      const response = await fetch(
        `http://localhost:8000/api/governance/approvals/${approvalId}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            actor_id: actorId,
            notes: "Approved via dashboard",
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        alert(`Approval failed: ${errorData.detail}`);
        return;
      }

      alert("Approval successful!");
      fetchApprovals();
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleReject = async (approvalId: string) => {
    const reason = prompt("Please provide rejection reason (min 10 characters):");

    if (!reason || reason.length < 10) {
      alert("Rejection reason must be at least 10 characters");
      return;
    }

    // Ensure user is authenticated
    const actorId = currentUser?.username || "anonymous";

    try {
      const response = await fetch(
        `http://localhost:8000/api/governance/approvals/${approvalId}/reject`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            actor_id: actorId,
            reason: reason,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        alert(`Rejection failed: ${errorData.detail}`);
        return;
      }

      alert("Rejection successful!");
      fetchApprovals();
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const formatTimeUntilExpiry = (seconds: number) => {
    if (seconds < 0) return "Expired";

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h`;
    }
    return `${hours}h ${minutes}m`;
  };

  const getRiskTierColor = (tier: string) => {
    switch (tier) {
      case "critical":
        return "bg-red-100 text-red-800 border-red-300";
      case "high":
        return "bg-orange-100 text-orange-800 border-orange-300";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "low":
        return "bg-green-100 text-green-800 border-green-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Governance & HITL Approvals</h1>
        <p className="text-gray-600">Human-in-the-loop approval workflows for critical system actions</p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b">
        {[
          { key: "pending", label: "Pending" },
          { key: "approved", label: "Approved" },
          { key: "rejected", label: "Rejected" },
          { key: "expired", label: "Expired" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSelectedTab(tab.key as any)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
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
          <p className="mt-4 text-gray-600">Loading approvals...</p>
        </div>
      )}

      {/* Approvals List */}
      {!loading && (
        <div className="space-y-4">
          {pendingApprovals.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <p className="text-gray-600">No {selectedTab} approvals</p>
            </div>
          ) : (
            pendingApprovals.map((approval) => (
              <div
                key={approval.approval_id}
                className="bg-white border rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRiskTierColor(
                          approval.risk_tier
                        )}`}
                      >
                        {approval.risk_tier.toUpperCase()}
                      </span>
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300">
                        {approval.approval_type.replace("_", " ").toUpperCase()}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {approval.action_description}
                    </h3>
                  </div>

                  {selectedTab === "pending" && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(approval.approval_id)}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                      >
                        ✓ Approve
                      </button>
                      <button
                        onClick={() => handleReject(approval.approval_id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                      >
                        ✗ Reject
                      </button>
                    </div>
                  )}
                </div>

                {/* Details */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Requested By</p>
                    <p className="font-mono font-medium">{approval.requested_by}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Requested At</p>
                    <p className="font-medium">{formatTimestamp(approval.requested_at)}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Expires</p>
                    <p className="font-medium">{formatTimestamp(approval.expires_at)}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Time Until Expiry</p>
                    <p className={`font-medium ${approval.time_until_expiry < 3600 ? "text-red-600" : ""}`}>
                      {formatTimeUntilExpiry(approval.time_until_expiry)}
                    </p>
                  </div>
                </div>

                {/* Approval ID */}
                <div className="mt-4 pt-4 border-t">
                  <p className="text-xs text-gray-500">
                    ID: <span className="font-mono">{approval.approval_id}</span>
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Quick Stats */}
      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-600">
          <strong>Total Approvals:</strong> {pendingApprovals.length} {selectedTab}
        </p>
      </div>
    </div>
  );
}
