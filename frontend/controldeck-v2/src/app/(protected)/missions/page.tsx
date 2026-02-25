"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from "@ui-core/components";
import { StatusPill } from "@ui-core/components";
import { 
  Plus, 
  Search,
  Filter,
  MoreHorizontal,
  Play,
  Pause,
  RotateCw,
  Target
} from "lucide-react";

// Mock Mission Data
const missions = [
  {
    id: "m-001",
    name: "Deploy v2.1 to Production",
    type: "deploy",
    status: "running",
    priority: "high",
    progress: 65,
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    agent: "picofred",
  },
  {
    id: "m-002",
    name: "Database Backup",
    type: "backup",
    status: "completed",
    priority: "medium",
    progress: 100,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    agent: "system",
  },
  {
    id: "m-003",
    name: "Health Check All Systems",
    type: "health",
    status: "pending",
    priority: "low",
    progress: 0,
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    agent: null,
  },
  {
    id: "m-004",
    name: "Agent Update",
    type: "update",
    status: "failed",
    priority: "high",
    progress: 45,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
    agent: "picofred",
  },
  {
    id: "m-005",
    name: "Log Rotation",
    type: "maintenance",
    status: "completed",
    priority: "low",
    progress: 100,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    agent: "system",
  },
];

const getStatusPill = (status: string) => {
  switch (status) {
    case "running":
      return <StatusPill status="live" pulse>Running</StatusPill>;
    case "completed":
      return <StatusPill status="safe">Completed</StatusPill>;
    case "failed":
      return <StatusPill status="down">Failed</StatusPill>;
    case "pending":
      return <StatusPill status="idle">Pending</StatusPill>;
    default:
      return <StatusPill status="idle">{status}</StatusPill>;
  }
};

const getPriorityBadge = (priority: string) => {
  switch (priority) {
    case "high":
      return <Badge variant="danger">High</Badge>;
    case "medium":
      return <Badge variant="warning">Medium</Badge>;
    case "low":
      return <Badge variant="info">Low</Badge>;
    default:
      return <Badge>{priority}</Badge>;
  }
};

export default function MissionsPage() {
  return (
    <DashboardLayout title="Missions" subtitle="Mission Control Center">
      <PageContainer>
        <PageHeader
          title="Missions"
          description="Verwalte und überwache alle System-Missionen"
          actions={
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Neue Mission
            </Button>
          }
        />

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Missionen suchen..."
                  className="w-full pl-9 pr-4 py-2 rounded-md border border-input bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                Filter
              </Button>
              <Button variant="outline" size="sm">
                Status
              </Button>
              <Button variant="outline" size="sm">
                Priorität
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Missions Table */}
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Mission</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Priorität</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Progress</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Agent</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Erstellt</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground"></th>
                  </tr>
                </thead>
                <tbody>
                  {missions.map((mission) => (
                    <tr key={mission.id} className="border-b border-border hover:bg-secondary/50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Target className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium">{mission.name}</p>
                            <p className="text-xs text-muted-foreground">{mission.id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">{getStatusPill(mission.status)}</td>
                      <td className="py-3 px-4">{getPriorityBadge(mission.priority)}</td>
                      <td className="py-3 px-4">
                        <div className="w-full max-w-[100px]">
                          <div className="flex justify-between text-xs mb-1">
                            <span>{mission.progress}%</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${mission.progress}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-muted-foreground">
                          {mission.agent || "—"}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-muted-foreground">
                          {new Date(mission.createdAt).toLocaleDateString("de-DE")}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1">
                          {mission.status === "running" && (
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Pause className="h-4 w-4" />
                            </Button>
                          )}
                          {mission.status === "pending" && (
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          {mission.status === "failed" && (
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <RotateCw className="h-4 w-4" />
                            </Button>
                          )}
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}