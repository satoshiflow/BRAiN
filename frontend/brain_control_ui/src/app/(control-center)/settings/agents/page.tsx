"use client";

import { useAgentsInfo, useSupervisorAgents } from "@/hooks/useAgents";

export default function AgentSettingsPage() {
  const infoQuery = useAgentsInfo();
  const agentsQuery = useSupervisorAgents();

  const info = infoQuery.data;

  // Supervisor liefert KEIN Array → prüfen
  const agentsRaw = agentsQuery.data;
  const agents = Array.isArray(agentsRaw?.agents)
    ? agentsRaw.agents
    : Array.isArray(agentsRaw)
    ? agentsRaw
    : [];

  return (
    <div className="flex flex-col gap-8 w-full">
      <div>
        <h1 className="brain-shell-title">Agents</h1>
        <p className="brain-shell-subtitle">Agenten-Konfiguration & Status</p>
      </div>

      <div className="brain-card">
        <div className="brain-card-header">
          <h2 className="brain-card-title">Agent System Info</h2>
        </div>

        <div className="flex flex-col gap-3 text-sm text-muted-foreground">
          {infoQuery.isLoading ? (
            <p>Lade Agent-Infos...</p>
          ) : (
            <>
              <p>Name: {info?.name ?? "–"}</p>
              <p>Status: {info?.status ?? "–"}</p>
              <p>Version: {info?.version ?? "–"}</p>
            </>
          )}
        </div>
      </div>

      <div className="brain-card">
        <div className="brain-card-header">
          <h2 className="brain-card-title">Supervisor Agents</h2>
        </div>

        <div className="flex flex-col gap-3 text-sm">
          {agentsQuery.isLoading ? (
            <p>Lade Agents...</p>
          ) : agents.length === 0 ? (
            <p className="text-muted-foreground">Keine Agents registriert.</p>
          ) : (
            agents.map((agent: any, idx: number) => (
              <div
                key={idx}
                className="flex justify-between items-center py-2 border-b border-border/50"
              >
                <span>{agent.name ?? "Unnamed Agent"}</span>
                <span className="text-muted-foreground">
                  {agent.state ?? "unknown"}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
