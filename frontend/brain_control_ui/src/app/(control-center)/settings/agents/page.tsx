"use client";

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

import { useAgentsInfo, useSupervisorAgents, AgentState } from "@/hooks/useAgents";

export default function AgentSettingsPage() {
  const infoQuery = useAgentsInfo();
  const agentsQuery = useSupervisorAgents();

  const info = infoQuery.data;
  const agents = agentsQuery.data ?? [];
  const loading = infoQuery.isLoading || agentsQuery.isLoading;

  const error = infoQuery.error || agentsQuery.error;

  const renderStateBadge = (state: AgentState) => {
    const label = state.toUpperCase();
    switch (state) {
      case "healthy":
        return <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/40">{label}</Badge>;
      case "degraded":
        return <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/40">{label}</Badge>;
      case "offline":
        return <Badge className="bg-red-500/10 text-red-400 border-red-500/40">{label}</Badge>;
      default:
        return <Badge className="bg-slate-500/10 text-slate-300 border-slate-500/40">{label}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Agent Settings</h2>
          <p className="text-sm text-muted-foreground">
            Übersicht über registrierte Agenten, deren Status und aktuelle Missionen.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            infoQuery.refetch();
            agentsQuery.refetch();
          }}
          disabled={loading}
        >
          {loading ? "Aktualisiere…" : "Refresh"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {(error as Error).message}
        </div>
      )}

      {info && (
        <Card>
          <CardHeader>
            <CardTitle>{info.name ?? "Agent Manager"}</CardTitle>
            <CardDescription>
              Version {info.version ?? "n/a"} – {info.description ?? "Verwaltet agentenbezogene Funktionen in BRAiN."}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground space-y-1">
            <p>Status: {info.status ?? "online"}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Registrierte Agenten</CardTitle>
          <CardDescription>
            Agenten, die vom Supervisor bekannt sind. Später können hier Agenten erstellt, editiert und deaktiviert
            werden.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {agents.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aktuell sind keine Agenten registriert. Sobald BRAiN eigene Agenten erzeugt oder du welche definierst,
              erscheinen sie hier.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="border-b border-border/60 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-2 py-2 text-left font-medium">Name</th>
                    <th className="px-2 py-2 text-left font-medium">ID</th>
                    <th className="px-2 py-2 text-left font-medium">State</th>
                    <th className="px-2 py-2 text-left font-medium">Last Heartbeat</th>
                    <th className="px-2 py-2 text-left font-medium">Current Mission</th>
                    <th className="px-2 py-2 text-left font-medium">Capabilities</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map((agent) => (
                    <tr key={agent.id} className="border-b border-border/40 last:border-0">
                      <td className="px-2 py-2 font-medium">{agent.name}</td>
                      <td className="px-2 py-2 text-xs text-muted-foreground">{agent.id}</td>
                      <td className="px-2 py-2">{renderStateBadge(agent.state)}</td>
                      <td className="px-2 py-2 text-xs text-muted-foreground">
                        {agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleString() : "–"}
                      </td>
                      <td className="px-2 py-2 text-xs text-muted-foreground">
                        {agent.current_mission_id ?? "–"}
                      </td>
                      <td className="px-2 py-2 text-xs text-muted-foreground">
                          {agent.capabilities?.length ? agent.capabilities.join(", ") : "–"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Später: Agent-Erstellung, Rollenprofile, Auto-Scaling, Routing-Regeln und Self-Healing direkt aus diesem Deck.
      </p>
    </div>
  );
}