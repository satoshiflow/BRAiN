"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@ui-core/components";
import { StatusPill, KpiCard } from "@ui-core/components";
import { 
  Activity,
  Database,
  Server,
  Wifi,
  CheckCircle,
  AlertCircle,
  XCircle
} from "lucide-react";

const healthChecks = [
  {
    name: "API Gateway",
    status: "healthy",
    latency: "45ms",
    uptime: "99.9%",
    lastCheck: new Date(Date.now() - 1000 * 30).toISOString(),
  },
  {
    name: "Redis",
    status: "healthy",
    latency: "2ms",
    uptime: "100%",
    lastCheck: new Date(Date.now() - 1000 * 30).toISOString(),
  },
  {
    name: "PostgreSQL",
    status: "healthy",
    latency: "12ms",
    uptime: "99.9%",
    lastCheck: new Date(Date.now() - 1000 * 30).toISOString(),
  },
  {
    name: "Mission Worker",
    status: "warning",
    latency: "120ms",
    uptime: "98.5%",
    lastCheck: new Date(Date.now() - 1000 * 30).toISOString(),
  },
  {
    name: "AXE Engine",
    status: "healthy",
    latency: "8ms",
    uptime: "99.9%",
    lastCheck: new Date(Date.now() - 1000 * 30).toISOString(),
  },
  {
    name: "Event Stream",
    status: "healthy",
    latency: "5ms",
    uptime: "100%",
    lastCheck: new Date(Date.now() - 1000 * 30).toISOString(),
  },
];

const getStatusIcon = (status: string) => {
  switch (status) {
    case "healthy":
      return <CheckCircle className="h-5 w-5 text-success" />;
    case "warning":
      return <AlertCircle className="h-5 w-5 text-warning" />;
    case "critical":
      return <XCircle className="h-5 w-5 text-danger" />;
    default:
      return <Activity className="h-5 w-5 text-muted-foreground" />;
  }
};

const getStatusPill = (status: string) => {
  switch (status) {
    case "healthy":
      return <StatusPill status="safe">Healthy</StatusPill>;
    case "warning":
      return <StatusPill status="degraded">Warning</StatusPill>;
    case "critical":
      return <StatusPill status="down">Critical</StatusPill>;
    default:
      return <StatusPill status="idle">Unknown</StatusPill>;
  }
};

export default function HealthPage() {
  return (
    <DashboardLayout title="Health" subtitle="System Health Monitoring">
      <PageContainer>
        <PageHeader
          title="System Health"
          description="Überwache den Status aller System-Komponenten"
        />

        {/* KPI Cards */}
        <Grid cols={4} className="mb-6">
          <KpiCard
            title="Overall Status"
            value="98%"
            status="positive"
            icon={<Activity className="h-4 w-4" />}
          />
          <KpiCard
            title="Services Online"
            value="5/6"
            status="warning"
            icon={<Server className="h-4 w-4" />}
          />
          <KpiCard
            title="Avg Latency"
            value="32ms"
            status="positive"
            icon={<Wifi className="h-4 w-4" />}
          />
          <KpiCard
            title="DB Connections"
            value="12"
            status="neutral"
            icon={<Database className="h-4 w-4" />}
          />
        </Grid>

        {/* Health Checks Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {healthChecks.map((check) => (
            <Card key={check.name}>
              <CardHeader className="flex flex-row items-center justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(check.status)}
                  <CardTitle className="text-base">{check.name}</CardTitle>
                </div>
                {getStatusPill(check.status)}
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Latency</span>
                    <span className="font-mono">{check.latency}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Uptime</span>
                    <span>{check.uptime}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Last Check</span>
                    <span className="text-xs">
                      {new Date(check.lastCheck).toLocaleTimeString("de-DE")}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </PageContainer>
    </DashboardLayout>
  );
}