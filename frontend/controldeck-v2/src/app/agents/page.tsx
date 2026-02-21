"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, Button, Badge } from "@ui-core/components";
import { StatusPill } from "@ui-core/components";
import { 
  Plus,
  Settings,
  Bot,
  Activity,
  CheckCircle,
  XCircle,
  Clock
} from "lucide-react";

const agents = [
  {
    id: "picofred",
    name: "PicoFred",
    status: "online",
    version: "1.2.0",
    lastSeen: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    tasksCompleted: 142,
    capabilities: ["mission", "backup", "health"],
  },
  {
    id: "worker-01",
    name: "Worker 01",
    status: "online",
    version: "1.1.5",
    lastSeen: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    tasksCompleted: 89,
    capabilities: ["mission", "deploy"],
  },
  {
    id: "worker-02",
    name: "Worker 02",
    status: "offline",
    version: "1.1.5",
    lastSeen: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    tasksCompleted: 56,
    capabilities: ["mission"],
  },
  {
    id: "system",
    name: "System Agent",
    status: "online",
    version: "2.0.0",
    lastSeen: new Date().toISOString(),
    tasksCompleted: 999,
    capabilities: ["backup", "maintenance", "health"],
  },
];

const getStatusIcon = (status: string) => {
  switch (status) {
    case "online":
      return <CheckCircle className="h-5 w-5 text-success" />;
    case "offline":
      return <XCircle className="h-5 w-5 text-danger" />;
    default:
      return <Clock className="h-5 w-5 text-muted-foreground" />;
  }
};

export default function AgentsPage() {
  return (
    <DashboardLayout title="Agents" subtitle="Agent Fleet Management">
      <PageContainer>
        <PageHeader
          title="Agents"
          description="Verwalte deine Agenten-Fleet"
          actions={
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Agent hinzufügen
            </Button>
          }
        />

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{agent.name}</CardTitle>
                    <CardDescription>{agent.id}</CardDescription>
                  </div>
                </div>
                {agent.status === "online" ? (
                  <StatusPill status="live" pulse>Online</StatusPill>
                ) : (
                  <StatusPill status="down">Offline</StatusPill>
                )}
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono">{agent.version}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Tasks</span>
                    <span>{agent.tasksCompleted}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Last Seen</span>
                    <span>{new Date(agent.lastSeen).toLocaleTimeString("de-DE")}</span>
                  </div>
                  <div className="pt-2">
                    <span className="text-xs text-muted-foreground">Capabilities</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {agent.capabilities.map((cap) => (
                        <Badge key={cap} variant="secondary" className="text-xs">
                          {cap}
                        </Badge>
                      ))}
                    </div>
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