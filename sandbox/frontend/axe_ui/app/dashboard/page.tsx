"use client";

import { useEffect, useState } from "react";

interface SystemStats {
  status: string;
  agents: number;
  missions: number;
  uptime: string;
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/health`);
      const data = await response.json();

      // Mock stats for now - replace with actual API calls
      setStats({
        status: data.status || "ok",
        agents: 5,
        missions: 12,
        uptime: "2h 34m",
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-slate-400">Loading dashboard...</p>
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

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">AXE Dashboard</h1>
        <p className="text-slate-400 mt-2">Auxiliary Execution Engine System Overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="System Status"
          value={stats?.status === "ok" ? "Operational" : "Unknown"}
          icon="✓"
          color="green"
        />
        <StatCard
          title="Active Agents"
          value={stats?.agents.toString() || "0"}
          icon="🤖"
          color="blue"
        />
        <StatCard
          title="Pending Missions"
          value={stats?.missions.toString() || "0"}
          icon="📋"
          color="purple"
        />
        <StatCard
          title="Uptime"
          value={stats?.uptime || "0m"}
          icon="⏱"
          color="yellow"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionButton
            label="Start Chat"
            description="Interact with AXE agent"
            icon="💬"
            href="/chat"
          />
          <ActionButton
            label="View Agents"
            description="Manage agent fleet"
            icon="🤖"
            href="/agents"
          />
          <ActionButton
            label="System Settings"
            description="Configure AXE"
            icon="⚙️"
            href="/settings"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Recent Activity</h2>
        <div className="space-y-3">
          <ActivityItem
            time="2 minutes ago"
            event="Mission completed: Deploy application"
            type="success"
          />
          <ActivityItem
            time="15 minutes ago"
            event="Agent CoderAgent started code generation"
            type="info"
          />
          <ActivityItem
            time="1 hour ago"
            event="Supervisor approved HIGH risk action"
            type="warning"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }: {
  title: string;
  value: string;
  icon: string;
  color: "green" | "blue" | "purple" | "yellow";
}) {
  const colorClasses = {
    green: "bg-green-500/20 border-green-500/50 text-green-400",
    blue: "bg-blue-500/20 border-blue-500/50 text-blue-400",
    purple: "bg-purple-500/20 border-purple-500/50 text-purple-400",
    yellow: "bg-yellow-500/20 border-yellow-500/50 text-yellow-400",
  };

  return (
    <div className={`p-6 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-slate-400 mt-1">{title}</div>
    </div>
  );
}

function ActionButton({ label, description, icon, href }: {
  label: string;
  description: string;
  icon: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="block p-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{icon}</span>
        <span className="font-semibold text-white">{label}</span>
      </div>
      <p className="text-sm text-slate-400">{description}</p>
    </a>
  );
}

function ActivityItem({ time, event, type }: {
  time: string;
  event: string;
  type: "success" | "info" | "warning";
}) {
  const dotColors = {
    success: "bg-green-500",
    info: "bg-blue-500",
    warning: "bg-yellow-500",
  };

  return (
    <div className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg">
      <div className={`w-2 h-2 rounded-full mt-2 ${dotColors[type]}`}></div>
      <div className="flex-1">
        <p className="text-sm text-white">{event}</p>
        <p className="text-xs text-slate-500 mt-1">{time}</p>
      </div>
    </div>
  );
}
