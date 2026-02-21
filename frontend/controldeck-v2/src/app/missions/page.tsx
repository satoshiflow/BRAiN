"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button, Skeleton } from "@ui-core/components";
import { StatusPill } from "@ui-core/components";
import { useMissions, useMissionHealth } from "@/hooks/use-api";
import { formatRelativeTime } from "@ui-core/utils";
import { 
  Plus, 
  Search,
  Filter,
  MoreHorizontal,
  Play,
  Pause,
  RotateCw,
  Target,
  AlertCircle,
  RefreshCw
} from "lucide-react";

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

const getPriorityBadge = (priority: number) => {
  if (priority >= 8) return <Badge variant="danger">High</Badge>;
  if (priority >= 5) return <Badge variant="warning">Medium</Badge>;
  return <Badge variant="info">Low</Badge>;
};

export default function MissionsPage() {
  const { data: missionsData, isLoading, isError, refetch } = useMissions(50);
  const { data: healthData } = useMissionHealth();

  if (isError) {
    return (
      <DashboardLayout title="Missions" subtitle="Mission Control Center">
        <PageContainer>
          <div className="flex flex-col items-center justify-center h-96">
            <AlertCircle className="h-12 w-12 text-danger mb-4" />
            <h2 className="text-xl font-semibold mb-2">Fehler beim Laden</h2>
            <p className="text-muted-foreground mb-4">
              Die Mission-Daten konnten nicht geladen werden.
            </p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Erneut versuchen
            </Button>
          </div>
        </PageContainer>
      </DashboardLayout>
    );
  }

  const missions = missionsData?.items ?? [];

  return (
    <DashboardLayout title="Missions" subtitle="Mission Control Center">
      <PageContainer>
        <PageHeader
          title="Missions"
          description={`${missionsData?.length ?? 0} Missionen in Queue • Health: ${healthData?.status ?? 'unknown'}`}
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
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Score</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Erstellt</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground"></th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i} className="border-b border-border">
                        <td className="py-3 px-4"><Skeleton className="h-8 w-32" /></td>
                        <td className="py-3 px-4"><Skeleton className="h-6 w-20" /></td>
                        <td className="py-3 px-4"><Skeleton className="h-6 w-16" /></td>
                        <td className="py-3 px-4"><Skeleton className="h-6 w-12" /></td>
                        <td className="py-3 px-4"><Skeleton className="h-6 w-24" /></td>
                        <td className="py-3 px-4"><Skeleton className="h-8 w-8" /></td>
                      </tr>
                    ))
                  ) : missions.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted-foreground">
                        <Target className="h-8 w-8 mx-auto mb-2" />
                        <p>Keine Missionen in der Queue</p>
                      </td>
                    </tr>
                  ) : (
                    missions.map((mission) => (
                      <tr key={mission.id} className="border-b border-border hover:bg-secondary/50">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3">
                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                              <Target className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                              <p className="font-medium">{mission.type}</p>
                              <p className="text-xs text-muted-foreground">{mission.id}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4">{getStatusPill(mission.status)}</td>
                        <td className="py-3 px-4">{getPriorityBadge(mission.priority)}</td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-sm">{mission.score.toFixed(2)}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-sm text-muted-foreground">
                            {formatRelativeTime(mission.created_at)}
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
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}