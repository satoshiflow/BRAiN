"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { KpiCard, Badge, StatusPill, Card, CardHeader, CardTitle, CardContent } from "@ui-core/components";
import { Button } from "@ui-core/components";
import { 
  Target, 
  Radio, 
  Activity, 
  Bot, 
  Plus, 
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Clock
} from "lucide-react";

// Mock Data für MVP
const kpiData = [
  {
    title: "Aktive Missions",
    value: 12,
    delta: { value: 8, label: "vs gestern" },
    status: "positive" as const,
    icon: <Target className="h-4 w-4" />,
  },
  {
    title: "System Events",
    value: 1,
    delta: { value: -2, label: "vs gestern" },
    status: "negative" as const,
    icon: <Radio className="h-4 w-4" />,
  },
  {
    title: "Agent Status",
    value: "4/5",
    delta: { value: 0, label: "online" },
    status: "neutral" as const,
    icon: <Bot className="h-4 w-4" />,
  },
  {
    title: "System Health",
    value: "98%",
    delta: { value: 2, label: "vs gestern" },
    status: "positive" as const,
    icon: <Activity className="h-4 w-4" />,
  },
];

const recentEvents = [
  {
    id: "1",
    type: "mission.completed",
    message: "Mission 'Deploy v2.1' erfolgreich abgeschlossen",
    severity: "success" as const,
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    source: "mission-control",
  },
  {
    id: "2",
    type: "agent.connected",
    message: "Agent 'picofred' verbunden",
    severity: "info" as const,
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    source: "agent-manager",
  },
  {
    id: "3",
    type: "system.warning",
    message: "Redis Memory > 75%",
    severity: "warning" as const,
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    source: "health-monitor",
  },
  {
    id: "4",
    type: "mission.started",
    message: "Mission 'Database Backup' gestartet",
    severity: "info" as const,
    timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    source: "mission-control",
  },
  {
    id: "5",
    type: "system.error",
    message: "API Gateway Timeout (3s)",
    severity: "danger" as const,
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    source: "api-gateway",
  },
];

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case "success":
      return <CheckCircle className="h-4 w-4 text-success" />;
    case "warning":
      return <AlertCircle className="h-4 w-4 text-warning" />;
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
    case "danger":
      return <Badge variant="danger">Error</Badge>;
    default:
      return <Badge variant="info">Info</Badge>;
  }
};

export default function DashboardPage() {
  return (
    <DashboardLayout title="Dashboard" subtitle="Systemübersicht & Echtzeit-Status">
      <PageContainer>
        {/* KPI Cards - Max 4 pro Row (Design System Rule) */}
        <Grid cols={4} className="mb-6">
          {kpiData.map((kpi) => (
            <KpiCard
              key={kpi.title}
              title={kpi.title}
              value={kpi.value}
              delta={kpi.delta}
              status={kpi.status}
              icon={kpi.icon}
            />
          ))}
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
              <div className="space-y-4">
                {recentEvents.map((event) => (
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
                          • {new Date(event.timestamp).toLocaleTimeString("de-DE")}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <Button variant="ghost" className="w-full mt-4" size="sm">
                Alle Events anzeigen
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="col-span-2 lg:col-span-1">
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Button className="w-full justify-start" size="lg">
                  <Plus className="h-4 w-4 mr-2" />
                  Neue Mission erstellen
                </Button>
                <Button variant="outline" className="w-full justify-start" size="lg">
                  <Bot className="h-4 w-4 mr-2" />
                  Agenten verwalten
                </Button>
                <Button variant="outline" className="w-full justify-start" size="lg">
                  <Radio className="h-4 w-4 mr-2" />
                  Events filtern
                </Button>
                <Button variant="outline" className="w-full justify-start" size="lg">
                  <Activity className="h-4 w-4 mr-2" />
                  Health Check ausführen
                </Button>
              </div>
            </CardContent>
          </Card>
        </Grid>
      </PageContainer>
    </DashboardLayout>
  );
}