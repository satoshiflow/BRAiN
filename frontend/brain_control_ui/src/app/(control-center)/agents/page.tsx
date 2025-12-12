"use client";

import { useState } from "react";
import { useAgentsInfo, useSupervisorAgents } from "@/hooks/useAgents";
import brainApi from "@/lib/brainApi";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

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

export default function AgentsPage() {
  const infoQuery = useAgentsInfo();
  const agentsQuery = useSupervisorAgents();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [command, setCommand] = useState("Statusbericht der letzten Mission.");
  const [commandResult, setCommandResult] = useState<string | null>(null);
  const [commandPending, setCommandPending] = useState(false);

  const info = infoQuery.data as any;

  const raw = agentsQuery.data as any;
  const agents: any[] = Array.isArray(raw?.agents)
    ? raw.agents
    : Array.isArray(raw)
    ? raw
    : [];

  const selected =
    agents.find((a) => a.id === selectedId) ?? (agents[0] ?? null);

  const counts = agents.reduce(
    (acc, agent) => {
      const bucket = classifyState(agent.state);
      acc[bucket] += 1;
      return acc;
    },
    { online: 0, degraded: 0, error: 0, unknown: 0 }
  );

  const handleSendCommand = async () => {
    if (!selected) return;
    setCommandPending(true);
    setCommandResult(null);

    try {
      const res = await brainApi.agents.chat({
        message: command,
        agent_id: selected.id,
        metadata: { source: "control-center" },
      });

      setCommandResult(JSON.stringify(res, null, 2));
    } catch (err: any) {
      setCommandResult(
        "Fehler beim Senden des Kommandos: " + (err?.message ?? String(err))
      );
    } finally {
      setCommandPending(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 w-full">
      {/* HEADER */}
      <div className="brain-shell-header">
        <div>
          <h1 className="brain-shell-title">Agents</h1>
          <p className="brain-shell-subtitle">
            Echtzeit-Übersicht, Details & Commands für BRAiN-Agenten.
          </p>
        </div>
      </div>

      {/* TOP SUMMARY */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* System */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Agent System</h2>
          </div>
          <div className="flex flex-col gap-2 text-sm text-muted-foreground">
            {infoQuery.isLoading ? (
              <p>Lade Agent System Info…</p>
            ) : infoQuery.isError ? (
              <p className="text-destructive">
                Fehler beim Laden: {(infoQuery.error as Error).message}
              </p>
            ) : (
              <>
                <p>
                  <span className="brain-meta">Name</span>
                  <br />
                  <span>{info?.name ?? "–"}</span>
                </p>
                <p>
                  <span className="brain-meta">Status</span>
                  <br />
                  <span>{info?.status ?? "–"}</span>
                </p>
                <p>
                  <span className="brain-meta">Version</span>
                  <br />
                  <span>{info?.version ?? "–"}</span>
                </p>
              </>
            )}
          </div>
        </div>

        {/* Cluster Summary */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Cluster Summary</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="brain-meta">Total</p>
              <p className="brain-card-value">{agents.length}</p>
            </div>
            <div>
              <p className="brain-meta">Online</p>
              <p className="brain-card-value">{counts.online}</p>
            </div>
            <div>
              <p className="brain-meta">Degraded</p>
              <p className="brain-card-value">{counts.degraded}</p>
            </div>
            <div>
              <p className="brain-meta">Error</p>
              <p className="brain-card-value text-destructive">
                {counts.error}
              </p>
            </div>
          </div>
        </div>

        {/* Hinweis */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Live Heartbeat</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Agentdaten werden regelmäßig aktualisiert (Polling durch React
            Query). Der letzte Heartbeat ist in der Detailansicht sichtbar.
          </p>
        </div>
      </div>

      {/* MAIN GRID: LIST + DETAIL + COMMAND */}
      <div className="grid gap-6 lg:grid-cols-[2fr,1.5fr]">
        {/* Agent List */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">Agents im Cluster</h2>
          </div>

          {agentsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Lade Agents…</p>
          ) : agentsQuery.isError ? (
            <p className="text-sm text-destructive">
              Fehler beim Laden: {(agentsQuery.error as Error).message}
            </p>
          ) : agents.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Keine Agents registriert.
            </p>
          ) : (
            <div className="mt-2 overflow-x-auto">
              <div className="min-w-[620px]">
                <div className="grid grid-cols-5 gap-4 border-b border-border pb-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  <div>Name</div>
                  <div>Status</div>
                  <div>Last Heartbeat</div>
                  <div>Mission</div>
                  <div>Generation / Meta</div>
                </div>

                <div className="mt-2 space-y-1 text-sm">
                  {agents.map((agent: any, idx: number) => {
                    const bucket = classifyState(agent.state);

                    let badgeClass =
                      "inline-flex items-center rounded-full px-3 py-1 text-xs";
                    if (bucket === "online") {
                      badgeClass += " bg-emerald-500/10 text-emerald-300";
                    } else if (bucket === "degraded") {
                      badgeClass += " bg-amber-500/10 text-amber-300";
                    } else if (bucket === "error") {
                      badgeClass += " bg-red-500/10 text-red-300";
                    } else {
                      badgeClass += " bg-slate-500/10 text-slate-300";
                    }

                    const isSelected =
                      (selected?.id ?? selectedId) === agent.id ||
                      (!selectedId && idx === 0);

                    return (
                      <button
                        key={agent.id ?? idx}
                        type="button"
                        onClick={() =>
                          setSelectedId(agent.id ?? String(idx))
                        }
                        className={`grid w-full grid-cols-5 gap-4 border-b border-border/50 py-2 text-left last:border-b-0 transition ${
                          isSelected ? "bg-muted/40" : "hover:bg-muted/20"
                        }`}
                      >
                        <div className="flex flex-col">
                          <span>
                            {agent.name ?? agent.id ?? "Unnamed Agent"}
                          </span>
                          {agent.id && (
                            <span className="text-[0.7rem] text-muted-foreground">
                              {agent.id}
                            </span>
                          )}
                        </div>
                        <div>
                          <span className={badgeClass}>
                            {agent.state ?? "unknown"}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {agent.last_heartbeat ??
                            agent.last_seen ??
                            "–"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {agent.current_mission_id ?? "–"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {agent.generation
                            ? `Gen ${agent.generation}`
                            : ""}
                          {agent.meta &&
                            ` · ${
                              Object.keys(agent.meta).length
                            } meta fields`}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* DETAIL + COMMAND */}
        <div className="flex flex-col gap-6">
          {/* Detail View */}
          <div className="brain-card">
            <div className="brain-card-header">
              <h2 className="brain-card-title">Agent Details</h2>
            </div>

            {selected ? (
              <div className="flex flex-col gap-3 text-sm text-muted-foreground">
                <p>
                  <span className="brain-meta">ID</span>
                  <br />
                  <span>{selected.id ?? "–"}</span>
                </p>
                <p>
                  <span className="brain-meta">Name</span>
                  <br />
                  <span>{selected.name ?? "–"}</span>
                </p>
                <p>
                  <span className="brain-meta">Status</span>
                  <br />
                  <span>{selected.state ?? "unknown"}</span>
                </p>
                <p>
                  <span className="brain-meta">Last Heartbeat</span>
                  <br />
                  <span>
                    {selected.last_heartbeat ??
                      selected.last_seen ??
                      "–"}
                  </span>
                </p>
                <p>
                  <span className="brain-meta">Current Mission</span>
                  <br />
                  <span>{selected.current_mission_id ?? "–"}</span>
                </p>
                {selected.capabilities && (
                  <p>
                    <span className="brain-meta">Capabilities</span>
                    <br />
                    <span>
                      {Array.isArray(selected.capabilities)
                        ? selected.capabilities.join(", ")
                        : String(selected.capabilities)}
                    </span>
                  </p>
                )}
                {selected.meta && (
                  <div>
                    <span className="brain-meta">Meta</span>
                    <pre className="mt-1 rounded-2xl bg-muted/40 p-3 text-xs overflow-x-auto">
                      {JSON.stringify(selected.meta, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Kein Agent ausgewählt.
              </p>
            )}
          </div>

          {/* Command Panel */}
          <div className="brain-card">
            <div className="brain-card-header">
              <h2 className="brain-card-title">Command Panel</h2>
            </div>

            {selected ? (
              <div className="flex flex-col gap-3 text-sm">
                <p className="text-muted-foreground">
                  Sende einen Befehl an{" "}
                  <span className="font-medium">
                    {selected.name ?? selected.id ?? "Agent"}
                  </span>
                  . Die Anfrage geht über <code>/api/agents/chat</code>.
                </p>

                <div>
                  <Label>Command</Label>
                  <Textarea
                    rows={4}
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                  />
                </div>

                {commandResult && (
                  <div className="text-xs text-muted-foreground whitespace-pre-wrap break-words rounded-2xl bg-muted/40 p-3">
                    {commandResult}
                  </div>
                )}

                <Button
                  type="button"
                  onClick={handleSendCommand}
                  disabled={commandPending}
                >
                  {commandPending ? "Sende..." : "Command senden"}
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Kein Agent ausgewählt.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
