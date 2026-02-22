"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { KpiCard, Badge, StatusPill, Card, CardHeader, CardTitle, CardContent, Skeleton } from "@ui-core/components";
import { Button } from "@ui-core/components";
import { useDashboardData } from "@/hooks/use-api";
import { formatRelativeTime } from "@ui-core/utils";
import { 
  Target, 
  Radio, 
  Activity, 
  Bot, 
  Plus, 
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  AlertTriangle
} from "lucide-react";

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case "success":
    case "info":
      return <CheckCircle className="h-4 w-4 text-success" />;
    case "warning":
      return <AlertTriangle className="h-4 w-4 text-warning" />;
    case "error":
    case "critical":
    case "danger":
      return <AlertCircle className="h-4 w-4 text-danger" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
};

const getSeverityBadge = (severity: string) => {
  switch (severity) {
    case "success":
      return <Badge variant="success">Success</Badge>;
    case "warning":
      return <Badge variant="warning">Warning</Badge>;
    case "error":
    case "critical":
      return <Badge variant="danger">Error</Badge>;
    default:
      return <Badge variant="info">Info</Badge>;
  }
};

export default function DashboardPage() {
  const { isLoading, isError, data, refetch } = useDashboardData();

  if (isError) {
    return (
      <DashboardLayout title="Dashboard" subtitle="Systemübersicht & Echtzeit-Status">
        <PageContainer>
          <div className="flex flex-col items-center justify-center h-96">
            <AlertCircle className="h-12 w-12 text-danger mb-4" />
            <h2 className="text-xl font-semibold mb-2">Fehler beim Laden</h2>
            <p className="text-muted-foreground mb-4">
              Die Dashboard-Daten konnten nicht geladen werden.
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

  return (
    <DashboardLayout title="Dashboard" subtitle="Systemübersicht & Echtzeit-Status">
      <PageContainer>
        {/* KPI Cards - Max 4 pro Row (Design System Rule) */}
        <Grid cols={4} className="mb-6">
          <KpiCard
            data-testid="kpi-active-missions"
            title="Aktive Missions"
            value={isLoading ? 0 : data.missions.active}
            loading={isLoading}
            icon={<Target className="h-4 w-4" />}
          />
          <KpiCard
            data-testid="kpi-pending-missions"
            title="Pending Missions"
            value={isLoading ? 0 : data.missions.pending}
            loading={isLoading}
            icon={<Clock className="h-4 w-4" />}
          />
          <KpiCard
            data-testid="kpi-error-events"
            title="Error Events"
            value={isLoading ? 0 : data.events.errorCount}
            status={data?.events.errorCount && data.events.errorCount > 0 ? "negative" : "positive"}
            loading={isLoading}
            icon={<Radio className="h-4 w-4" />}
          />
          <KpiCard
            data-testid="kpi-system-health"
            title="System Health"
            value={isLoading ? "—" : (data.health?.status === "ok" ? "OK" : "DEGRADED")}
            status={isLoading ? undefined : (data.health?.status === "ok" ? "positive" : "negative")}
            loading={isLoading}
            icon={<Activity className="h-4 w-4" />}
          />
        </Grid>

        {/* Main Content Grid */}
        <Grid cols={2} gap="lg">
          {/* Event Feed */}
          <Card className="col-span-2 lg:col-span-1">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Event Feed</CardTitle>
              <StatusPill status="live" pulse>
                LIVE
              </StatusPill>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : (
                <>
                  <div className="space-y-4">
                    {data.events.recent.slice(0, 5).map((event) => (
                      <div
                        key={event.id}
                        className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50"
                      >
                        {getSeverityIcon(event.severity)}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {event.message}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            {getSeverityBadge(event.severity)}
                            <span className="text-xs text-muted-foreground">
                              {event.source}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              • {formatRelativeTime(event.created_at)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <Button variant="ghost" className="w-full mt-4" size="sm" asChild>
                    <a href="/events">
                      Alle Events anzeigen
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </a>
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="col-span-2 lg:col-span-1">
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Button data-testid="quick-action-new-mission" className="w-full justify-start" size="lg" asChild>
                  <a href="/missions">
                    <Plus className="h-4 w-4 mr-2" />
                    Neue Mission erstellen
                  </a>
                </Button>
                <Button data-testid="quick-action-agents" variant="outline" className="w-full justify-start" size="lg" asChild>
                  <a href="/agents">
                    <Bot className="h-4 w-4 mr-2" />
                    Agenten verwalten
                  </a>
                </Button>
                <Button data-testid="quick-action-events" variant="outline" className="w-full justify-start" size="lg" asChild>
                  <a href="/events">
                    <Radio className="h-4 w-4 mr-2" />
                    Events filtern
                  </a>
                </Button>
                <Button data-testid="quick-action-health" variant="outline" className="w-full justify-start" size="lg" asChild>
                  <a href="/health">
                    <Activity className="h-4 w-4 mr-2" />
                    Health Check ausführen
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        </Grid>

        {/* Mission Queue Preview */}
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Mission Queue</CardTitle>
            <Button variant="outline" size="sm" asChild>
              <a href="/missions">Alle anzeigen</a>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : data.missions.items.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-8 w-8 mx-auto mb-2" />
                <p>Keine Missionen in der Queue</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {data.missions.items.slice(0, 5).map((mission) => (
                  <div
                    key={mission.id}
                    className="flex items-center justify-between py-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-2 w-2 rounded-full ${
                        mission.status === 'running' ? 'bg-success' :
                        mission.status === 'pending' ? 'bg-warning' :
                        mission.status === 'failed' ? 'bg-danger' :
                        'bg-muted'
                      }`} />
                      <div>
                        <p className="font-medium">{mission.type}</p>
                        <p className="text-xs text-muted-foreground">{mission.id}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge variant={
                        mission.status === 'running' ? 'success' :
                        mission.status === 'pending' ? 'warning' :
                        mission.status === 'failed' ? 'danger' :
                        'muted'
                      }>
                        {mission.status}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        P{mission.priority}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}