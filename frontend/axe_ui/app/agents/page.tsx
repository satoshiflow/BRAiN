"use client";

import { useEffect, useState } from "react";

interface Agent {
  id: string;
  name: string;
  status: "active" | "idle" | "error";
  type: string;
  tasks_completed: number;
  last_active: string;
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      // Mock data for now - replace with actual API call
      const mockAgents: Agent[] = [
        {
          id: "supervisor",
          name: "SupervisorAgent",
          status: "active",
          type: "Constitutional Guardian",
          tasks_completed: 142,
          last_active: "1 minute ago",
        },
        {
          id: "coder",
          name: "CoderAgent",
          status: "active",
          type: "Code Specialist",
          tasks_completed: 87,
          last_active: "3 minutes ago",
        },
        {
          id: "ops",
          name: "OpsAgent",
          status: "idle",
          type: "Operations Specialist",
          tasks_completed: 56,
          last_active: "15 minutes ago",
        },
        {
          id: "architect",
          name: "ArchitectAgent",
          status: "active",
          type: "Architecture Auditor",
          tasks_completed: 23,
          last_active: "5 minutes ago",
        },
        {
          id: "axe",
          name: "AXEAgent",
          status: "active",
          type: "Conversational Assistant",
          tasks_completed: 311,
          last_active: "Just now",
        },
      ];

      setAgents(mockAgents);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch agents");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-slate-400">Loading agents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-900/20 border border-red-500/50 rounded-lg">
        <h3 className="text-red-400 font-semibold mb-2">Error</h3>
        <p className="text-slate-300">{error}</p>
      </div>
    );
  }

  const activeCount = agents.filter((a) => a.status === "active").length;
  const idleCount = agents.filter((a) => a.status === "idle").length;
  const errorCount = agents.filter((a) => a.status === "error").length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Agent Fleet</h1>
        <p className="text-slate-400 mt-2">Manage and monitor all constitutional agents</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
          <div className="text-2xl font-bold text-white">{agents.length}</div>
          <div className="text-sm text-slate-400">Total Agents</div>
        </div>
        <div className="p-4 bg-green-900/20 border border-green-500/50 rounded-lg">
          <div className="text-2xl font-bold text-green-400">{activeCount}</div>
          <div className="text-sm text-slate-400">Active</div>
        </div>
        <div className="p-4 bg-yellow-900/20 border border-yellow-500/50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-400">{idleCount}</div>
          <div className="text-sm text-slate-400">Idle</div>
        </div>
        <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
          <div className="text-2xl font-bold text-red-400">{errorCount}</div>
          <div className="text-sm text-slate-400">Error</div>
        </div>
      </div>

      {/* Agents List */}
      <div className="space-y-4">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-start justify-between">
              {/* Agent Info */}
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-2xl">
                  🤖
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                  <p className="text-sm text-slate-400 mt-1">{agent.type}</p>
                  <div className="flex items-center gap-4 mt-3">
                    <span className="text-xs text-slate-500">
                      ID: <span className="font-mono">{agent.id}</span>
                    </span>
                    <span className="text-xs text-slate-500">
                      Last active: {agent.last_active}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status */}
              <div className="flex flex-col items-end gap-3">
                <StatusBadge status={agent.status} />
                <div className="text-right">
                  <div className="text-2xl font-bold text-white">
                    {agent.tasks_completed}
                  </div>
                  <div className="text-xs text-slate-400">Tasks completed</div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-4 pt-4 border-t border-slate-800 flex gap-2">
              <button className="px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors">
                View Logs
              </button>
              <button className="px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors">
                Send Command
              </button>
              <button className="px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors">
                View Metrics
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Agent["status"] }) {
  const styles = {
    active: "bg-green-500/20 border-green-500/50 text-green-400",
    idle: "bg-yellow-500/20 border-yellow-500/50 text-yellow-400",
    error: "bg-red-500/20 border-red-500/50 text-red-400",
  };

  const labels = {
    active: "Active",
    idle: "Idle",
    error: "Error",
  };

  return (
    <span
      className={`px-3 py-1 text-xs font-semibold rounded-full border ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}
