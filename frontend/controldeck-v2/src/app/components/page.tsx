"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardContent,
  KpiCard,
  ConsoleFeed,
  CircularProgress,
  Timeline,
  HeatmapGrid,
  HeatmapStats,
  LineChart,
  Sparkline,
  StatusPill,
  Badge
} from "@ui-core/components";
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Wifi,
  AlertCircle,
  CheckCircle,
  Server
} from "lucide-react";

// Demo Data
const consoleEvents = [
  {
    id: "1",
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    message: "Mission 'Deploy v2.1' completed successfully",
    severity: "success" as const,
    source: "mission-control",
  },
  {
    id: "2",
    timestamp: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
    message: "Agent 'picofred' connected to queue",
    severity: "info" as const,
    source: "agent-manager",
  },
  {
    id: "3",
    timestamp: new Date(Date.now() - 1000 * 60 * 3).toISOString(),
    message: "Warning: Redis memory usage at 78%",
    severity: "warning" as const,
    source: "health-monitor",
  },
  {
    id: "4",
    timestamp: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    message: "Database connection pool exhausted",
    severity: "error" as const,
    source: "postgres",
    details: { max_connections: 100, active: 100 },
  },
  {
    id: "5",
    timestamp: new Date(Date.now() - 1000 * 60 * 1).toISOString(),
    message: "Critical: API Gateway timeout",
    severity: "critical" as const,
    source: "api-gateway",
  },
];

const timelineEvents = [
  {
    id: "1",
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    title: "System Startup",
    description: "All services initialized",
    severity: "success" as const,
  },
  {
    id: "2",
    timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    title: "Mission Queue Cleared",
    description: "Processed 50 pending missions",
    severity: "info" as const,
  },
  {
    id: "3",
    timestamp: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
    title: "High Memory Usage",
    description: "Redis memory exceeded threshold",
    severity: "warning" as const,
  },
  {
    id: "4",
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    title: "Database Slow Query",
    description: "Query took 4.2s to complete",
    severity: "warning" as const,
  },
  {
    id: "5",
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    title: "Mission Completed",
    description: "Deploy v2.1 finished successfully",
    severity: "success" as const,
  },
];

const heatmapCells = [
  { id: "1", label: "API Gateway", status: "healthy" as const, value: 99, sublabel: "45ms latency" },
  { id: "2", label: "Auth Service", status: "healthy" as const, value: 98, sublabel: "12ms latency" },
  { id: "3", label: "Mission Queue", status: "warning" as const, value: 75, sublabel: "120ms latency" },
  { id: "4", label: "Event Stream", status: "healthy" as const, value: 100, sublabel: "5ms latency" },
  { id: "5", label: "Worker Node 1", status: "healthy" as const, value: 95, sublabel: "8ms latency" },
  { id: "6", label: "Worker Node 2", status: "critical" as const, value: 45, sublabel: "Timeout" },
  { id: "7", label: "Redis Cache", status: "warning" as const, value: 78, sublabel: "Memory high" },
  { id: "8", label: "PostgreSQL", status: "healthy" as const, value: 97, sublabel: "12ms latency" },
];

const chartData = [
  { timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(), value: 45 },
  { timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(), value: 52 },
  { timestamp: new Date(Date.now() - 1000 * 60 * 20).toISOString(), value: 48 },
  { timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(), value: 65 },
  { timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(), value: 58 },
  { timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(), value: 72 },
  { timestamp: new Date().toISOString(), value: 68 },
];

export default function ComponentsDemoPage() {
  return (
    <DashboardLayout title="Components" subtitle="Phase 2 Component Showcase">
      <PageContainer>
        <PageHeader
          title="Component Library"
          description="Advanced UI Components for ControlDeck v2"
        />

        {/* ConsoleFeed Demo */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Console Feed</h2>
          <ConsoleFeed 
            events={consoleEvents} 
            maxLines={10}
            autoScroll
          />
        </section>

        {/* CircularProgress & KPIs */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Progress Indicators</h2>
          <Grid cols={4}>
            <Card className="p-6 flex flex-col items-center">
              <CircularProgress 
                value={75} 
                size="lg" 
                label="CPU Usage"
                sublabel="12 cores"
              />
            </Card>
            <Card className="p-6 flex flex-col items-center">
              <CircularProgress 
                value={45} 
                size="lg" 
                color="warning"
                label="Memory"
                sublabel="18GB / 32GB"
              />
            </Card>
            <Card className="p-6 flex flex-col items-center">
              <CircularProgress 
                value={92} 
                size="lg" 
                color="success"
                label="Storage"
                sublabel="920GB / 1TB"
              />
            </Card>
            <Card className="p-6 flex flex-col items-center">
              <CircularProgress 
                value={100} 
                size="lg" 
                color="success"
                label="Network"
                sublabel="Connected"
              />
            </Card>
          </Grid>
        </section>

        {/* LineChart & Sparklines */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Charts</h2>
          <Grid cols={2}>
            <LineChart 
              data={chartData}
              title="CPU Usage (30min)"
              color="primary"
              showArea
              height={200}
              formatYAxis={(v) => `${v}%`}
            />
            <LineChart 
              data={chartData.map(d => ({ ...d, value: d.value * 0.8 + 20 }))}
              title="Memory Usage (30min)"
              color="warning"
              showArea
              height={200}
              formatYAxis={(v) => `${v}%`}
            />
          </Grid>
        </section>

        {/* HeatmapGrid */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">System Health Heatmap</h2>
          <Card className="p-6">
            <HeatmapStats cells={heatmapCells} className="mb-4" />
            <HeatmapGrid 
              cells={heatmapCells}
              columns={4}
              showValues
              showLabels
            />
          </Card>
        </section>

        {/* Timeline */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Event Timeline</h2>
          <Card className="p-6">
            <Timeline events={timelineEvents} />
          </Card>
        </section>

        {/* Sparklines in KPI Cards */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Sparkline KPIs</h2>
          <Grid cols={4}>
            <KpiCard
              title="CPU Load"
              value="68%"
              delta={{ value: 5, label: "vs avg" }}
              status="positive"
              icon={<Cpu className="h-4 w-4" />}
            />
            <KpiCard
              title="Memory"
              value="12.4 GB"
              delta={{ value: -2, label: "vs avg" }}
              status="positive"
              icon={<HardDrive className="h-4 w-4" />}
            />
            <KpiCard
              title="Network"
              value="1.2 Gbps"
              delta={{ value: 8, label: "vs avg" }}
              status="positive"
              icon={<Wifi className="h-4 w-4" />}
            />
            <KpiCard
              title="Uptime"
              value="99.9%"
              icon={<Activity className="h-4 w-4" />}
            />
          </Grid>
        </section>

        {/* Component Usage Notes */}
        <Card className="p-6 bg-secondary/30">
          <CardHeader>
            <CardTitle className="text-base">Component Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p><strong>ConsoleFeed:</strong> Terminal-ähnliche Event-Anzeige mit Severity-Farben und Timestamps</p>
            <p><strong>CircularProgress:</strong> Ring-Progress für Agenten-Status oder Resource-Usage</p>
            <p><strong>LineChart:</strong> Zeitserien-Charts für Metrics (CPU, Memory, etc.)</p>
            <p><strong>HeatmapGrid:</strong> System-Status Übersicht mit Farbkodierung</p>
            <p><strong>Timeline:</strong> Chronologische Event-Darstellung mit Gruppierung</p>
            <p><strong>Sparkline:</strong> Mini-Charts für KPI-Karten</p>
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}