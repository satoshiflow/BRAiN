"use client";

import { useState } from "react";
import {
  useAgentRegister,
  useAgentHeartbeat,
  useAgentDeregister,
  useSupervisorAgents,
} from "@/hooks/useAgents";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  HeartPulse,
  Power,
  UserPlus,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function parseMeta(metaRaw: string): any | undefined {
  if (!metaRaw.trim()) return undefined;
  try {
    return JSON.parse(metaRaw);
  } catch {
    return { raw: metaRaw };
  }
}

export default function LifecycleDeckPage() {
  const [agentId, setAgentId] = useState("agent-local-dev");
  const [agentName, setAgentName] = useState("Local Dev Agent");
  const [capabilities, setCapabilities] = useState("planner,executor");
  const [metaRaw, setMetaRaw] = useState("");

  const registerMutation = useAgentRegister();
  const heartbeatMutation = useAgentHeartbeat();
  const deregisterMutation = useAgentDeregister();
  const supervisorAgents = useSupervisorAgents();

  const agents = supervisorAgents.data ?? [];

  const handleRegister = () => {
    registerMutation.mutate({
      agent_id: agentId,
      name: agentName,
      capabilities: capabilities
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean),
      meta: parseMeta(metaRaw),
    });
  };

  const handleHeartbeat = () => {
    heartbeatMutation.mutate({
      agent_id: agentId,
      status: "online",
      meta: parseMeta(metaRaw),
    });
  };

  const handleDeregister = () => {
    deregisterMutation.mutate({
      agent_id: agentId,
    });
  };

  return (
    <div className="brain-shell">
      <div className="brain-shell-header">
        <div>
          <div className="brain-shell-title">Agent Lifecycle</div>
          <div className="brain-shell-subtitle">
            Registrierung, Heartbeats & Deregistrierung von BRAiN-Agenten.
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        {/* Control Panel */}
        <section className="brain-card">
          <div className="brain-card-header">
            <div className="brain-card-title">Lifecycle Control Panel</div>
            <Badge variant="outline" className="text-xs">
              Manual · Dev
            </Badge>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="agent-id">Agent ID</Label>
                <Input
                  id="agent-id"
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  placeholder="z.B. planner-01"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="agent-name">Name</Label>
                <Input
                  id="agent-name"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="Lesbarer Agentenname"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="capabilities">Capabilities (CSV)</Label>
                <Input
                  id="capabilities"
                  value={capabilities}
                  onChange={(e) => setCapabilities(e.target.value)}
                  placeholder="planner, critic, executor"
                />
                <p className="text-[0.7rem] text-muted-foreground">
                  Liste von Fähigkeiten, z.B. planner,executor,critic.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="meta">Meta (optional, JSON)</Label>
                <Textarea
                  id="meta"
                  value={metaRaw}
                  onChange={(e) => setMetaRaw(e.target.value)}
                  rows={6}
                  placeholder='{"env": "local", "note": "dev agent"}'
                />
                <p className="text-[0.7rem] text-muted-foreground">
                  Wird als JSON geparst. Fällt bei Fehlern auf ein einfaches
                  <code>meta.raw</code>-Feld zurück.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2">
                <Button
                  type="button"
                  onClick={handleRegister}
                  size="sm"
                  className="flex items-center gap-1"
                  disabled={registerMutation.isPending}
                >
                  <UserPlus className="h-4 w-4" />
                  Register
                </Button>
                <Button
                  type="button"
                  onClick={handleHeartbeat}
                  size="sm"
                  variant="outline"
                  className="flex items-center gap-1"
                  disabled={heartbeatMutation.isPending}
                >
                  <HeartPulse className="h-4 w-4" />
                  Heartbeat
                </Button>
                <Button
                  type="button"
                  onClick={handleDeregister}
                  size="sm"
                  variant="destructive"
                  className="flex items-center gap-1"
                  disabled={deregisterMutation.isPending}
                >
                  <Power className="h-4 w-4" />
                  Deregister
                </Button>
              </div>

              {(registerMutation.error ||
                heartbeatMutation.error ||
                deregisterMutation.error) && (
                <p className="text-[0.7rem] text-red-500">
                  Fehler bei Lifecycle-Call – siehe Network-Tab im Browser.
                </p>
              )}

              {(registerMutation.isSuccess ||
                heartbeatMutation.isSuccess ||
                deregisterMutation.isSuccess) && (
                <p className="text-[0.7rem] text-emerald-400">
                  Lifecycle-Event erfolgreich an das Backend gesendet.
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Supervisor Agents */}
        <section className="brain-card">
          <div className="brain-card-header">
            <div className="brain-card-title">Supervisor Agents</div>
            <Badge variant="outline" className="text-xs">
              Live
            </Badge>
          </div>
          {supervisorAgents.isLoading && (
            <p className="text-xs text-muted-foreground">Lade Agents…</p>
          )}
          {supervisorAgents.error && (
            <p className="text-xs text-red-500">
              Fehler beim Laden der Agents. Backend-Endpunkte vorhanden?
            </p>
          )}
          <div className="mt-2 max-h-[260px] overflow-auto rounded-2xl border border-border/60">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Heartbeat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={3}
                      className="text-xs text-muted-foreground"
                    >
                      Keine Agents registriert.
                    </TableCell>
                  </TableRow>
                )}
                {agents.map((agent: any, idx: number) => (
                  <TableRow key={agent.id ?? idx}>
                    <TableCell className="text-xs font-medium">
                      {agent.name ?? agent.id ?? "Unknown"}
                    </TableCell>
                    <TableCell className="text-xs">
                      <span className="inline-flex items-center gap-1">
                        <span className="brain-dot brain-dot-online" />
                        {agent.status ?? agent.state ?? "online"}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs">
                      {agent.last_heartbeat ?? agent.last_seen ?? "–"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      </div>
    </div>
  );
}
