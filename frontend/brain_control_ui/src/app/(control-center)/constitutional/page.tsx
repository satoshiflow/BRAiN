"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Shield,
  Code,
  Rocket,
  Building2,
  MessageSquare,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock
} from "lucide-react";
import { useSupervisor, useCoder, useOps, useArchitect, useAXE } from "@/hooks/useAgents";
import { SupervisorDashboard } from "@/components/control-center/constitutional/supervisor-dashboard";
import { CoderInterface } from "@/components/control-center/constitutional/coder-interface";
import { OpsPanel } from "@/components/control-center/constitutional/ops-panel";
import { ArchitectInterface } from "@/components/control-center/constitutional/architect-interface";
import { AXEChatInterface } from "@/components/control-center/constitutional/axe-chat-interface";

export default function ConstitutionalAgentsPage() {
  const supervisor = useSupervisor();
  const axe = useAXE();

  // Get metrics for overview cards
  const supervisorMetrics = supervisor.getMetrics.data;
  const systemStatus = axe.getSystemStatus.data;

  return (
    <div className="brain-shell">
      <div className="brain-shell-header">
        <div>
          <h1 className="brain-shell-title">Constitutional Agents</h1>
          <p className="brain-shell-subtitle">
            DSGVO- und EU AI Act-konforme Agenten mit integrierter Supervision und Human-in-the-Loop
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-green-500/50 text-green-500">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Constitutional Framework Active
          </Badge>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-5 mb-6">
        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-500" />
              Supervisor
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-2xl font-bold">
                {supervisorMetrics?.total_supervision_requests ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Total Requests</p>
              {supervisorMetrics && (
                <div className="flex items-center gap-2 text-xs mt-2">
                  <span className="text-green-500">
                    ✓ {supervisorMetrics.approved_actions}
                  </span>
                  <span className="text-red-500">
                    ✗ {supervisorMetrics.denied_actions}
                  </span>
                  <span className="text-yellow-500">
                    ⏳ {supervisorMetrics.human_approvals_pending}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <Code className="w-4 h-4 text-purple-500" />
              Coder
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-2xl font-bold">DSGVO</p>
              <p className="text-xs text-muted-foreground">Secure Code Generation</p>
              <Badge variant="outline" className="text-xs mt-2">
                Privacy by Design
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <Rocket className="w-4 h-4 text-orange-500" />
              Ops
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-2xl font-bold">Deploy</p>
              <p className="text-xs text-muted-foreground">Safe Operations</p>
              <Badge variant="outline" className="text-xs mt-2">
                Auto Rollback
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <Building2 className="w-4 h-4 text-cyan-500" />
              Architect
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-2xl font-bold">EU</p>
              <p className="text-xs text-muted-foreground">Compliance Audit</p>
              <Badge variant="outline" className="text-xs mt-2">
                AI Act + DSGVO
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-green-500" />
              AXE
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-2xl font-bold">
                {systemStatus?.status === "operational" ? "✓" : "⏳"}
              </p>
              <p className="text-xs text-muted-foreground">Assistant Status</p>
              <Badge variant="outline" className="text-xs mt-2">
                Conversational AI
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs Interface */}
      <Tabs defaultValue="supervisor" className="space-y-6">
        <TabsList className="bg-brain-panel border border-white/5">
          <TabsTrigger value="supervisor" className="data-[state=active]:bg-brain-accent">
            <Shield className="w-4 h-4 mr-2" />
            Supervisor
          </TabsTrigger>
          <TabsTrigger value="coder" className="data-[state=active]:bg-brain-accent">
            <Code className="w-4 h-4 mr-2" />
            Coder
          </TabsTrigger>
          <TabsTrigger value="ops" className="data-[state=active]:bg-brain-accent">
            <Rocket className="w-4 h-4 mr-2" />
            Operations
          </TabsTrigger>
          <TabsTrigger value="architect" className="data-[state=active]:bg-brain-accent">
            <Building2 className="w-4 h-4 mr-2" />
            Architect
          </TabsTrigger>
          <TabsTrigger value="axe" className="data-[state=active]:bg-brain-accent">
            <MessageSquare className="w-4 h-4 mr-2" />
            AXE Chat
          </TabsTrigger>
        </TabsList>

        <TabsContent value="supervisor" className="space-y-4">
          <SupervisorDashboard />
        </TabsContent>

        <TabsContent value="coder" className="space-y-4">
          <CoderInterface />
        </TabsContent>

        <TabsContent value="ops" className="space-y-4">
          <OpsPanel />
        </TabsContent>

        <TabsContent value="architect" className="space-y-4">
          <ArchitectInterface />
        </TabsContent>

        <TabsContent value="axe" className="space-y-4">
          <AXEChatInterface />
        </TabsContent>
      </Tabs>

      {/* Compliance Footer */}
      <Card className="brain-card mt-6 border-brain-gold/20">
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-3 text-sm">
            <div>
              <h4 className="font-semibold text-brain-gold mb-2">DSGVO Compliance</h4>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li>✓ Art. 22 - Automated Decision Making</li>
                <li>✓ Art. 25 - Privacy by Design</li>
                <li>✓ Art. 44 - International Transfers</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-brain-gold mb-2">EU AI Act</h4>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li>✓ Art. 16 - Human Oversight</li>
                <li>✓ Art. 52 - Transparency</li>
                <li>✓ Prohibited Practices Detection</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-brain-gold mb-2">Safety Framework</h4>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li>✓ Risk-based Supervision (4 levels)</li>
                <li>✓ Constitutional LLM Checks</li>
                <li>✓ Comprehensive Audit Trail</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
