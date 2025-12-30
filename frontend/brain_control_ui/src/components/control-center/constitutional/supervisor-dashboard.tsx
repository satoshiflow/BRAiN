"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSupervisor, type RiskLevel, type SupervisionRequest } from "@/hooks/useAgents";
import { Shield, CheckCircle2, XCircle, AlertTriangle, Clock, User } from "lucide-react";

export function SupervisorDashboard() {
  const { superviseAction, getMetrics, isSupervising } = useSupervisor();

  const [requestingAgent, setRequestingAgent] = useState("TestAgent");
  const [action, setAction] = useState("");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("low");
  const [reason, setReason] = useState("");
  const [contextJson, setContextJson] = useState("{}");

  const metrics = getMetrics.data;

  const handleSupervise = () => {
    let parsedContext = {};
    try {
      parsedContext = JSON.parse(contextJson);
    } catch (e) {
      alert("Invalid JSON in context field");
      return;
    }

    const request: SupervisionRequest = {
      requesting_agent: requestingAgent,
      action,
      risk_level: riskLevel,
      context: parsedContext,
      reason: reason || undefined,
    };

    superviseAction.mutate(request);
  };

  return (
    <div className="space-y-6">
      {/* Metrics Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm">Total Requests</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{metrics?.total_supervision_requests ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              Approved
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-500">{metrics?.approved_actions ?? 0}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {metrics && metrics.total_supervision_requests > 0
                ? `${((metrics.approved_actions / metrics.total_supervision_requests) * 100).toFixed(1)}%`
                : "0%"}
            </p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              Denied
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-500">{metrics?.denied_actions ?? 0}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {metrics && metrics.total_supervision_requests > 0
                ? `${((metrics.denied_actions / metrics.total_supervision_requests) * 100).toFixed(1)}%`
                : "0%"}
            </p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <User className="w-4 h-4 text-yellow-500" />
              Pending HITL
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-500">
              {metrics?.human_approvals_pending ?? 0}
            </p>
            <p className="text-xs text-muted-foreground mt-1">Awaiting human approval</p>
          </CardContent>
        </Card>
      </div>

      {/* Supervision Request Form */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">Request Supervision</CardTitle>
          <CardDescription>
            Test the constitutional supervision framework with custom requests
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="agent">Requesting Agent</Label>
              <Input
                id="agent"
                value={requestingAgent}
                onChange={(e) => setRequestingAgent(e.target.value)}
                placeholder="e.g., CoderAgent, OpsAgent"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="risk">Risk Level</Label>
              <Select value={riskLevel} onValueChange={(v) => setRiskLevel(v as RiskLevel)}>
                <SelectTrigger id="risk">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      LOW - Read-only operations
                    </div>
                  </SelectItem>
                  <SelectItem value="medium">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-yellow-500" />
                      MEDIUM - Write operations
                    </div>
                  </SelectItem>
                  <SelectItem value="high">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-orange-500" />
                      HIGH - Personal data, production
                    </div>
                  </SelectItem>
                  <SelectItem value="critical">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-red-500" />
                      CRITICAL - Irreversible, system-wide
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="action">Action</Label>
            <Input
              id="action"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g., deploy_to_production, generate_odoo_module"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Input
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is this action needed?"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="context">Context (JSON)</Label>
            <Textarea
              id="context"
              value={contextJson}
              onChange={(e) => setContextJson(e.target.value)}
              placeholder='{"environment": "production", "uses_personal_data": true}'
              className="font-mono text-xs"
              rows={4}
            />
          </div>

          <Button
            onClick={handleSupervise}
            disabled={isSupervising || !action}
            className="w-full"
          >
            {isSupervising ? "Processing..." : "Request Supervision"}
          </Button>

          {/* Response Display */}
          {superviseAction.data && (
            <Alert className={superviseAction.data.approved ? "border-green-500/50" : "border-red-500/50"}>
              <AlertDescription className="space-y-2">
                <div className="flex items-center gap-2 font-semibold">
                  {superviseAction.data.approved ? (
                    <><CheckCircle2 className="w-4 h-4 text-green-500" /> Approved</>
                  ) : (
                    <><XCircle className="w-4 h-4 text-red-500" /> Denied</>
                  )}
                </div>
                <p className="text-sm">{superviseAction.data.reason}</p>
                {superviseAction.data.human_oversight_required && (
                  <div className="flex items-center gap-2 text-yellow-500 text-sm mt-2">
                    <User className="w-4 h-4" />
                    Human oversight required
                    {superviseAction.data.human_oversight_token && (
                      <Badge variant="outline" className="font-mono text-xs">
                        {superviseAction.data.human_oversight_token}
                      </Badge>
                    )}
                  </div>
                )}
                {superviseAction.data.policy_violations.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-orange-500">Policy Violations:</p>
                    <ul className="text-xs space-y-1 mt-1">
                      {superviseAction.data.policy_violations.map((v, i) => (
                        <li key={i}>• {v}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-2">
                  Audit ID: {superviseAction.data.audit_id}
                </p>
              </AlertDescription>
            </Alert>
          )}

          {superviseAction.error && (
            <Alert className="border-red-500/50">
              <AlertDescription>
                <p className="text-red-500 font-semibold">Error</p>
                <p className="text-sm">{superviseAction.error.message}</p>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Risk Level Guide */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">Risk Level Guide</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <div className="w-3 h-3 rounded-full bg-green-500 mt-1" />
              <div>
                <p className="font-semibold">LOW</p>
                <p className="text-xs text-muted-foreground">
                  Read-only operations, no side effects. Auto-approved after LLM check.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-3 h-3 rounded-full bg-yellow-500 mt-1" />
              <div>
                <p className="font-semibold">MEDIUM</p>
                <p className="text-xs text-muted-foreground">
                  Write operations, reversible changes. Auto-approved after policy + LLM check.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-3 h-3 rounded-full bg-orange-500 mt-1" />
              <div>
                <p className="font-semibold">HIGH</p>
                <p className="text-xs text-muted-foreground">
                  Personal data processing, production changes. <strong>Requires human approval</strong> (EU AI Act Art. 16).
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-3 h-3 rounded-full bg-red-500 mt-1" />
              <div>
                <p className="font-semibold">CRITICAL</p>
                <p className="text-xs text-muted-foreground">
                  Irreversible operations, system-wide impact. <strong>Requires human approval</strong> (DSGVO Art. 22).
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
