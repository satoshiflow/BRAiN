"use client";

import { useSupervisorStatus } from "@/hooks/useSupervisor";
import { useSupervisorAgents } from "@/hooks/useAgents";
import {
  useMissionsInfo,
  useMissionsHealth,
  useMissionQueue,
  useMissionsAgentsInfo,
} from "@/hooks/useMissions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function normalizeAgents(raw: any): any[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw.agents)) return raw.agents;
  if (Array.isArray(raw.items)) return raw.items;
  return [];
}

function normalizeMissions(raw: any): any[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw.queue)) return raw.queue;
  return [];
}

export default function SupervisorDeckPage() {
  const supervisorStatusQuery = useSupervisorStatus();
  const supervisorAgentsQuery = useSupervisorAgents();
  const missionsInfoQuery = useMissionsInfo();
  const missionsHealthQuery = useMissionsHealth();
  const missionQueueQuery = useMissionQueue();
  const missionsAgentsInfoQuery = useMissionsAgentsInfo();

  const supervisorStatus = supervisorStatusQuery.data as any;
  const missionsInfo = missionsInfoQuery.data as any;
  const missionsHealth = missionsHealthQuery.data as any;

  const supervisorAgents = normalizeAgents(supervisorAgentsQuery.data);
  const missionQueue = normalizeMissions(missionQueueQuery.data);
  const missionAgents = normalizeAgents(missionsAgentsInfoQuery.data);

  const totalSupervisorAgents = supervisorAgents.length;
  const totalMissionAgents = missionAgents.length;
  const totalQueuedMissions = missionQueue.length;

  const runningMissions = missionQueue.filter(
    (m: any) =>
      typeof m.status === "string" &&
      m.status.toLowerCase().includes("running"),
  ).length;

  const waitingMissions = missionQueue.filter((m: any) => {
    if (typeof m.status !== "string") return false;
    const s = m.status.toLowerCase();
    return s.includes("pending") || s.includes("queued") || s.includes("waiting");
  }).length;

  return (
    <div className="brain-shell">
      <div className="brain-shell-header">
        <div>
          <h1 className="brain-shell-title">Supervisor Deck</h1>
          <p className="brain-shell-subtitle">
            Übersicht über den BRAiN Supervisor, Missionssystem und registrierte
            Agents.
          </p>
        </div>
      </div>

      {/* TOP GRID */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="brain-card">
          <CardHeader className="brain-card-header">
            <CardTitle className="brain-card-title">Supervisor Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {supervisorStatusQuery.isLoading ? (
              <p className="text-muted-foreground">Lade Supervisor Status…</p>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <span
                    className={`brain-dot ${
                      supervisorStatus?.status === "ok"
                        ? "brain-dot-online"
                        : "brain-dot-error"
                    }`}
                  />
                  <span className="font-medium">
                    {supervisorStatus?.status ?? "unknown"}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Version: {supervisorStatus?.version ?? "n/a"}
                </p>
                {supervisorStatus?.message && (
                  <p className="text-xs text-muted-foreground">
                    {supervisorStatus.message}
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header">
            <CardTitle className="brain-card-title">Missionssystem</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {missionsInfoQuery.isLoading ? (
              <p className="text-muted-foreground">Lade Missionsinfo…</p>
            ) : (
              <>
                <div>
                  <p className="brain-meta">Name</p>
                  <p className="brain-card-value">
                    {missionsInfo?.name ?? "Missions"}
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Status: {missionsHealth?.status ?? "unknown"}
                </p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="brain-meta">In Queue</p>
                    <p className="brain-card-value">
                      {totalQueuedMissions}
                    </p>
                  </div>
                  <div>
                    <p className="brain-meta">Running</p>
                    <p className="brain-card-value">
                      {runningMissions}
                    </p>
                  </div>
                  <div>
                    <p className="brain-meta">Waiting</p>
                    <p className="brain-card-value">
                      {waitingMissions}
                    </p>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header">
            <CardTitle className="brain-card-title">
              Agents (Supervisor / Missions)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                Supervisor Agents
              </span>
              <span className="font-semibold">
                {totalSupervisorAgents}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                Missions Agents
              </span>
              <span className="font-semibold">{totalMissionAgents}</span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Hier siehst du, welche Agents der Supervisor und das Missionssystem
              aktuell kennen. Die Details findest du unten in den Tabellen.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* TABLES */}
      <div className="grid gap-6 lg:grid-cols-2 mt-6">
        {/* SUPERVISOR AGENTS */}
        <Card className="brain-card">
          <CardHeader className="brain-card-header">
            <CardTitle className="brain-card-title">Supervisor Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {supervisorAgentsQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">
                Lade Supervisor Agents…
              </p>
            ) : supervisorAgents.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Keine Supervisor Agents gemeldet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Agent ID</TableHead>
                      <TableHead>Rolle</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Heartbeat</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {supervisorAgents.map((agent: any, idx: number) => (
                      <TableRow key={agent.id ?? agent.agent_id ?? idx}>
                        <TableCell className="font-mono text-xs">
                          {agent.id ?? agent.agent_id ?? "-"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {agent.role ?? agent.type ?? "n/a"}
                        </TableCell>
                        <TableCell className="text-xs">
                          <Badge
                            variant="outline"
                            className="border-border text-[0.7rem] capitalize"
                          >
                            {agent.state ?? agent.status ?? "unknown"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-[0.7rem] text-muted-foreground">
                          {agent.last_heartbeat ?? agent.last_seen ?? "n/a"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* MISSIONS AGENTS */}
        <Card className="brain-card">
          <CardHeader className="brain-card-header">
            <CardTitle className="brain-card-title">Missions Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {missionsAgentsInfoQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">
                Lade Missions Agents…
              </p>
            ) : missionAgents.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Keine Missions Agents gemeldet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name / ID</TableHead>
                      <TableHead>Typ</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Meta</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {missionAgents.map((agent: any, idx: number) => (
                      <TableRow key={agent.id ?? idx}>
                        <TableCell className="text-xs font-medium">
                          {agent.name ?? agent.id ?? "Unknown"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {agent.role ?? agent.type ?? "n/a"}
                        </TableCell>
                        <TableCell className="text-xs">
                          <Badge
                            variant="outline"
                            className="border-border text-[0.7rem] capitalize"
                          >
                            {agent.state ?? agent.status ?? "unknown"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-[0.7rem] text-muted-foreground">
                          {agent.meta ? Object.keys(agent.meta).length : 0} keys
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
