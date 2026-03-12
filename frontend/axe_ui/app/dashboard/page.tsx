"use client";

import { useEffect, useState } from "react";
import { getApiHealth } from "@/lib/api";
import { getControlDeckBase } from "@/lib/config";

interface SystemStats {
  status: string;
  agents: number;
  missions: number;
  uptime: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const controlDeckAgentsUrl = `${getControlDeckBase()}/agents`;
  const usingFallback = stats?.agents === 5 && stats?.missions === 12 && stats?.uptime === "2h 34m";

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const data = await getApiHealth();

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
      <div>
        <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-cyan-300/70">Systems Overview Surface</p>
        <h1 className="axe-surface-title text-3xl font-bold text-white">AXE Presence Matrix</h1>
        <p className="mt-2 text-slate-400">Live operator view of system health, mission load, and agent orchestration posture.</p>
      </div>

      {usingFallback && (
        <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Runtime surface is currently using compatibility telemetry. The upcoming AXE presence backend can replace these fallback values without changing this UI.
        </div>
      )}

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
          title="Mission Load"
          value={stats?.missions.toString() || "0"}
          icon="◎"
          color="purple"
        />
        <StatCard
          title="Uptime"
          value={stats?.uptime || "0m"}
          icon="◌"
          color="yellow"
        />
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">Control Relays</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionButton
            label="Start Chat"
            description="Interact with AXE agent"
            icon="💬"
            href="/chat"
          />
          <ActionButton
            label="Agents (ControlDeck)"
            description="Open fleet management"
            icon="🧭"
            href={controlDeckAgentsUrl}
            external
          />
          <ActionButton
            label="System Settings"
            description="Configure AXE"
            icon="⚙️"
            href="/settings"
          />
        </div>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">Recent Signal Log</h2>
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
          <ActivityItem time="1 hour ago" event="Supervisor approved HIGH risk action" type="warning" />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="axe-panel rounded-xl p-5">
          <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-cyan-300/70">External Agents</p>
          <h3 className="axe-surface-title text-lg font-semibold text-white">Relay Handshake</h3>
          <p className="mt-2 text-sm text-slate-400">
            Placeholder lane for downstream agent relays. Intended for future `axe_presence` aggregation.
          </p>
          <div className="mt-4 flex gap-2 text-xs">
            <span className="axe-chip rounded-full px-3 py-1">dispatch</span>
            <span className="axe-chip rounded-full px-3 py-1">sync</span>
          </div>
        </div>

        <div className="axe-panel rounded-xl p-5">
          <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-amber-300/70">Robot Relay</p>
          <h3 className="axe-surface-title text-lg font-semibold text-white">Execution Link</h3>
          <p className="mt-2 text-sm text-slate-400">
            Placeholder surface for robotic handoff confidence, last contact, and execution confirmation requirements.
          </p>
          <div className="mt-4 flex gap-2 text-xs">
            <span className="axe-chip rounded-full px-3 py-1">standby</span>
            <span className="axe-chip rounded-full px-3 py-1">confirm before execute</span>
          </div>
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
    green: "border-emerald-400/35 bg-emerald-500/10 text-emerald-200",
    blue: "border-cyan-400/35 bg-cyan-500/10 text-cyan-200",
    purple: "border-fuchsia-400/30 bg-fuchsia-500/10 text-fuchsia-200",
    yellow: "border-amber-400/35 bg-amber-500/10 text-amber-200",
  };

  return (
    <div className={`rounded-xl border p-6 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="mt-1 text-sm text-slate-300">{title}</div>
    </div>
  );
}

function ActionButton({ label, description, icon, href, external }: {
  label: string;
  description: string;
  icon: string;
  href: string;
  external?: boolean;
}) {
  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      className="block rounded-lg border border-cyan-500/20 bg-slate-900/70 p-4 transition-colors hover:border-cyan-400/45 hover:bg-slate-800"
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{icon}</span>
        <span className="font-semibold text-white">{label}</span>
      </div>
      <p className="text-sm text-slate-300">{description}</p>
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
      <div className={`mt-2 h-2 w-2 rounded-full ${dotColors[type]}`}></div>
      <div className="flex-1">
        <p className="text-sm text-white">{event}</p>
        <p className="text-xs text-slate-500 mt-1">{time}</p>
      </div>
    </div>
  );
}
