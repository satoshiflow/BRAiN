"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from "@ui-core/components";
import { 
  Filter, 
  Search,
  AlertCircle,
  CheckCircle,
  Info,
  XCircle,
  Clock
} from "lucide-react";

// Mock Events Data
const events = [
  {
    id: "evt-001",
    type: "mission.completed",
    message: "Mission 'Deploy v2.1' erfolgreich abgeschlossen",
    severity: "info",
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    source: "mission-control",
    details: { missionId: "m-001", duration: 120 },
  },
  {
    id: "evt-002",
    type: "agent.connected",
    message: "Agent 'picofred' verbunden",
    severity: "info",
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    source: "agent-manager",
    details: { agentId: "picofred", version: "1.2.0" },
  },
  {
    id: "evt-003",
    type: "system.warning",
    message: "Redis Memory > 75%",
    severity: "warning",
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    source: "health-monitor",
    details: { memory: "78%", threshold: "75%" },
  },
  {
    id: "evt-004",
    type: "mission.failed",
    message: "Mission 'Agent Update' fehlgeschlagen",
    severity: "error",
    timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    source: "mission-control",
    details: { missionId: "m-004", error: "Connection timeout" },
  },
  {
    id: "evt-005",
    type: "system.error",
    message: "API Gateway Timeout (3s)",
    severity: "error",
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    source: "api-gateway",
    details: { endpoint: "/api/missions", timeout: 3000 },
  },
  {
    id: "evt-006",
    type: "mission.started",
    message: "Mission 'Database Backup' gestartet",
    severity: "info",
    timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    source: "mission-control",
    details: { missionId: "m-002" },
  },
  {
    id: "evt-007",
    type: "agent.disconnected",
    message: "Agent 'worker-02' getrennt",
    severity: "warning",
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    source: "agent-manager",
    details: { agentId: "worker-02", reason: "heartbeat_timeout" },
  },
];

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case "error":
      return <XCircle className="h-5 w-5 text-danger" />;
    case "warning":
      return <AlertCircle className="h-5 w-5 text-warning" />;
    case "success":
      return <CheckCircle className="h-5 w-5 text-success" />;
    default:
      return <Info className="h-5 w-5 text-info" />;
  }
};

const getSeverityBadge = (severity: string) => {
  switch (severity) {
    case "error":
      return <Badge variant="danger">Error</Badge>;
    case "warning":
      return <Badge variant="warning">Warning</Badge>;
    case "success":
      return <Badge variant="success">Success</Badge>;
    default:
      return <Badge variant="info">Info</Badge>;
  }
};

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) return "gerade eben";
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} Min. ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} Std. ago`;
  return date.toLocaleDateString("de-DE");
};

export default function EventsPage() {
  return (
    <DashboardLayout title="Events" subtitle="System Event Stream">
      <PageContainer>
        <PageHeader
          title="Events"
          description="Systemweite Events und Logs"
          actions={
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" />
              Filter
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
                  placeholder="Events suchen..."
                  className="w-full pl-9 pr-4 py-2 rounded-md border border-input bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <Button variant="outline" size="sm">Alle</Button>
              <Button variant="outline" size="sm">Info</Button>
              <Button variant="outline" size="sm">Warning</Button>
              <Button variant="outline" size="sm">Error</Button>
            </div>
          </CardContent>
        </Card>

        {/* Events List */}
        <Card>
          <CardHeader>
            <CardTitle>Event History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-4 p-4 rounded-lg border border-border hover:bg-secondary/30 transition-colors"
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getSeverityIcon(event.severity)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium">{event.message}</p>
                      {getSeverityBadge(event.severity)}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(event.timestamp)}
                      </span>
                      <span>•</span>
                      <span>{event.source}</span>
                      <span>•</span>
                      <span className="font-mono text-xs">{event.type}</span>
                    </div>
                    {event.details && (
                      <div className="mt-2 p-2 rounded bg-muted/50 font-mono text-xs overflow-x-auto">
                        <pre>{JSON.stringify(event.details, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}