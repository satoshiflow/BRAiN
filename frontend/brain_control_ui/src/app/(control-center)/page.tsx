"use client";

import Link from "next/link";
import { useSupervisorStatus } from "@/hooks/useSupervisor";
import { useAgentsInfo, useSupervisorAgents } from "@/hooks/useAgents";
import { useMissionQueue, useMissionHealth } from "@/hooks/useMissions";

type AgentStateBucket = "online" | "degraded" | "error" | "unknown";

function classifyState(rawState: string | undefined): AgentStateBucket {
  if (!rawState) return "unknown";
  const s = rawState.toLowerCase();

  if (["healthy", "online", "ready", "running"].some((k) => s.includes(k))) {
    return "online";
  }
  if (["degraded", "warning"].some((k) => s.includes(k))) {
    return "degraded";
  }
  if (["error", "failed", "down", "offline"].some((k) => s.includes(k))) {
    return "error";
  }
  return "unknown";
}

export default function ControlCenterOverview() {
  // System / Backend
  const supervisorQuery = useSupervisorStatus();

  // Agents
  const agentsInfoQuery = useAgentsInfo();
  const supervisorAgentsQuery = useSupervisorAgents();

  // Missions
  const missionQueueQuery = useMissionQueue();
  const missionHealthQuery = useMissionHealth();

  const backendHealth = supervisorQuery.data as any;
  const agentsInfo = agentsInfoQuery.data as any;

  // Agents-Array robust extrahieren
  const rawAgents = supervisorAgentsQuery.data as any;
  const agents: any[] = Array.isArray(rawAgents?.agents)
    ? rawAgents.agents
    : Array.isArray(rawAgents)
    ? rawAgents
    : [];

  const agentCounts = agents.reduce(
    (acc, agent) => {
      const bucket = classifyState(agent.state ?? agent.status);
      acc[bucket] += 1;
      return acc;
    },
    { online: 0, degraded: 0, error: 0, unknown: 0 }
  );

  // Missions-Array robust extrahieren (API kann {queue: [...]} o.Ä. liefern)
  const rawMissions = missionQueueQuery.data as any;
  const missions: any[] = Array.isArray(rawMissions)
    ? rawMissions
    : Array.isArray(rawMissions?.queue)
    ? rawMissions.queue
    : [];

  const missionHealth = missionHealthQuery.data as any;

  const missionsRunning = missions.filter(
    (m: any) =>
      typeof m.status === "string" &&
      m.status.toLowerCase().includes("running")
  ).length;

  const missionsWaiting = missions.filter(
    (m: any) =>
      typeof m.status === "string" &&
      (m.status.toLowerCase().includes("pending") ||
        m.status.toLowerCase().includes("queued") ||
        m.status.toLowerCase().includes("waiting"))
  ).length;

  const backendStatusText = backendHealth?.status ?? "unknown";

  const backendOk =
    typeof backendStatusText === "string" &&
    ["ok", "healthy", "online"].includes(backendStatusText.toLowerCase());

  const missionsStatusText = missionHealth?.status ?? "unknown";

  return (
    <div className="flex flex-col gap-10 w-full">
      {/* HEADER */}
      <div className="brain-shell-header">
        <div>
          <h1 className="brain-shell-title">BRAIN Control Center</h1>
          <p className="brain-shell-subtitle">
            Zentrales Frontend für Cluster, Missionen, Agenten, Health & Settings.
          </p>
        </div>
      </div>

      {/* TOP ROW: System / Agents / Missions / Health */}
      <div className="grid gap-6 xl:grid-cols-4 lg:grid-cols-2">
        {/* SYSTEM STATUS */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Systemstatus</h2>
            <Link
              href="/settings"
              className="text-xs text-primary hover:underline"
            >
              Settings
            </Link>
          </div>
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex items-center gap-2">
              <span
                className={`brain-dot ${
                  backendOk ? "brain-dot-online" : "brain-dot-error"
                }`}
              />
              <span className="text-muted-foreground">
                {supervisorQuery.isLoading
                  ? "Prüfe Backend Health…"
                  : backendStatusText}
              </span>
            </div>
            <div>
              <p className="brain-meta">Version</p>
              <p className="brain-card-value">
                {backendHealth?.version ?? "–"}
              </p>
            </div>
            {backendHealth?.message && (
              <p className="text-xs text-muted-foreground">
                {backendHealth.message}
              </p>
            )}
          </div>
        </div>

        {/* AGENTS */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Aktive Agenten</h2>
            <Link
              href="/agents"
              className="text-xs text-primary hover:underline"
            >
              Agents Deck
            </Link>
          </div>
          <div className="flex flex-col gap-4 text-sm">
            <div>
              <p className="brain-meta">Agent System</p>
              <p className="brain-card-value">
                {agentsInfo?.name ?? "Agents"}
              </p>
              <p className="text-xs text-muted-foreground">
                {agentsInfo?.status ?? "–"}
              </p>
            </div>
            <div className="grid grid-cols-4 gap-3">
              <div>
                <p className="brain-meta">Total</p>
                <p className="brain-card-value">{agents.length}</p>
              </div>
              <div>
                <p className="brain-meta">Online</p>
                <p className="brain-card-value">{agentCounts.online}</p>
              </div>
              <div>
                <p className="brain-meta">Degraded</p>
                <p className="brain-card-value">
                  {agentCounts.degraded}
                </p>
              </div>
              <div>
                <p className="brain-meta">Error</p>
                <p className="brain-card-value text-destructive">
                  {agentCounts.error}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* MISSIONS */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Missions</h2>
            <Link
              href="/missions"
              className="text-xs text-primary hover:underline"
            >
              Mission Deck
            </Link>
          </div>
          <div className="flex flex-col gap-4 text-sm">
            <div>
              <p className="brain-meta">Status</p>
              <p className="brain-card-value">
                {missionsStatusText}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <p className="brain-meta">In Queue</p>
                <p className="brain-card-value">{missions.length}</p>
              </div>
              <div>
                <p className="brain-meta">Running</p>
                <p className="brain-card-value">{missionsRunning}</p>
              </div>
              <div>
                <p className="brain-meta">Waiting</p>
                <p className="brain-card-value">{missionsWaiting}</p>
              </div>
            </div>
            {missions.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Nächste Mission:{" "}
                <span className="font-medium">
                  {missions[0].type ?? missions[0].id}
                </span>
              </p>
            )}
          </div>
        </div>

        {/* HEALTH / OVERVIEW */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Cluster Health</h2>
          </div>
          <div className="flex flex-col gap-3 text-sm text-muted-foreground">
            <p>
              Überblick über den BRAiN Cluster. Details zu Agents, Missions
              und LLM findest du in den jeweiligen Decks.
            </p>
            <ul className="mt-1 space-y-1 text-xs">
              <li>• Backend Health über /api/health</li>
              <li>• Missions Health über /api/missions/health</li>
              <li>• Agents Info über /api/agents/info</li>
              <li>• Supervisor Agents über /api/missions/agents/info</li>
            </ul>
          </div>
        </div>
      </div>

      {/* SECOND ROW: Services & Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* SERVICES OVERVIEW */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Decks & Services</h2>
          </div>
          <div className="grid gap-3 text-sm">
            <Link
              href="/"
              className="flex items-center justify-between rounded-2xl border px-4 py-3 hover:bg-muted/50 transition"
            >
              <div>
                <p className="font-medium">Control Deck</p>
                <p className="text-xs text-muted-foreground">
                  Übersicht über System, Agents, Missionen & Health.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">Open →</span>
            </Link>
            <Link
              href="/agents"
              className="flex items-center justify-between rounded-2xl border px-4 py-3 hover:bg-muted/50 transition"
            >
              <div>
                <p className="font-medium">Agenten Deck</p>
                <p className="text-xs text-muted-foreground">
                  Detail-Ansicht & Commands für BRAiN-Agenten.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">Open →</span>
            </Link>
            <Link
              href="/settings/llm"
              className="flex items-center justify-between rounded-2xl border px-4 py-3 hover:bg-muted/50 transition"
            >
              <div>
                <p className="font-medium">LLM Settings</p>
                <p className="text-xs text-muted-foreground">
                  Provider, Model, Host & Limits des zentralen LLM-Clients.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">Open →</span>
            </Link>
          </div>
        </div>

        {/* RECENT ACTIVITY (vorerst statisch / später mit Logs) */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Recent Activity</h2>
          </div>
          <div className="flex flex-col gap-3 text-sm text-muted-foreground">
            <div className="flex items-center gap-3">
              <span className="brain-dot brain-dot-online" />
              <span>Backend Health Check erfolgreich</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="brain-dot brain-dot-online" />
              <span>Agenteninformationen geladen</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="brain-dot brain-dot-paused" />
              <span>Missionsqueue überwacht</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Später kannst du hier echte Logs aus dem Mission System,
              Supervisor und AXE anzeigen.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
/* ------------------------------------------------------------------
   HOOKS für Missions-API
-------------------------------------------------------------------*/