"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useOps, type DeploymentRequest } from "@/hooks/useAgents";
import { Rocket, RotateCcw, CheckCircle2, AlertTriangle, Activity } from "lucide-react";

export function OpsPanel() {
  const { deployApplication, rollbackDeployment, isDeploying, isRollingBack } = useOps();

  // Deployment State
  const [appName, setAppName] = useState("");
  const [version, setVersion] = useState("");
  const [environment, setEnvironment] = useState<"development" | "staging" | "production">("development");

  // Rollback State
  const [rollbackAppName, setRollbackAppName] = useState("");
  const [rollbackEnvironment, setRollbackEnvironment] = useState("");
  const [backupId, setBackupId] = useState("");

  const handleDeploy = () => {
    const request: DeploymentRequest = {
      app_name: appName,
      version,
      environment,
      config: {},
    };
    deployApplication.mutate(request);
  };

  const handleRollback = () => {
    rollbackDeployment.mutate({
      app_name: rollbackAppName,
      environment: rollbackEnvironment,
      backup_id: backupId,
    });
  };

  const getRiskBadge = (env: string) => {
    switch (env) {
      case "development":
        return <Badge className="bg-green-500/20 text-green-500 border-green-500/50">LOW Risk</Badge>;
      case "staging":
        return <Badge className="bg-yellow-500/20 text-yellow-500 border-yellow-500/50">MEDIUM Risk</Badge>;
      case "production":
        return <Badge className="bg-red-500/20 text-red-500 border-red-500/50">CRITICAL Risk</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="brain-card border-orange-500/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-orange-500/10">
              <Rocket className="w-6 h-6 text-orange-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg mb-2">Safe Operations & Deployment</h3>
              <p className="text-sm text-muted-foreground">
                OpsAgent handles deployments with automatic risk assessment, pre-deployment checks,
                health monitoring, and automatic rollback on failure.
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                <Badge variant="outline" className="text-xs">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Pre-deployment Checks
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <Activity className="w-3 h-3 mr-1" />
                  Health Monitoring
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <RotateCcw className="w-3 h-3 mr-1" />
                  Auto Rollback
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Deployment Form */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">Deploy Application</CardTitle>
          <CardDescription>
            Deploy applications with automatic supervisor approval for production
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert className="border-orange-500/50">
            <AlertDescription className="text-xs">
              <p className="font-semibold mb-1">Production Deployments Require Approval</p>
              <p>
                Production deployments are classified as CRITICAL risk and automatically trigger
                human oversight workflow (EU AI Act Art. 16).
              </p>
            </AlertDescription>
          </Alert>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="appName">Application Name</Label>
              <Input
                id="appName"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                placeholder="e.g., brain-backend"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="version">Version</Label>
              <Input
                id="version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="e.g., 1.2.3"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="environment">Environment</Label>
            <Select
              value={environment}
              onValueChange={(v) => setEnvironment(v as "development" | "staging" | "production")}
            >
              <SelectTrigger id="environment">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="development">
                  Development (LOW risk - auto-approved)
                </SelectItem>
                <SelectItem value="staging">
                  Staging (MEDIUM risk - auto-approved)
                </SelectItem>
                <SelectItem value="production">
                  Production (CRITICAL risk - requires approval)
                </SelectItem>
              </SelectContent>
            </Select>
            <div className="mt-2">{getRiskBadge(environment)}</div>
          </div>

          <Button
            onClick={handleDeploy}
            disabled={isDeploying || !appName || !version}
            className="w-full"
          >
            {isDeploying ? "Deploying..." : "Deploy Application"}
          </Button>

          {deployApplication.data && (
            <Alert className="border-green-500/50">
              <AlertDescription className="space-y-2">
                <div className="flex items-center gap-2 font-semibold text-green-500">
                  <CheckCircle2 className="w-4 h-4" />
                  Deployment Request Submitted
                </div>
                <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                  {JSON.stringify(deployApplication.data, null, 2)}
                </pre>
              </AlertDescription>
            </Alert>
          )}

          {deployApplication.error && (
            <Alert className="border-red-500/50">
              <AlertDescription>
                <p className="text-red-500 font-semibold">Deployment Failed</p>
                <p className="text-sm">{deployApplication.error.message}</p>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Rollback Form */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">Rollback Deployment</CardTitle>
          <CardDescription>
            Rollback to a previous version using backup snapshots
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="rollbackAppName">Application Name</Label>
              <Input
                id="rollbackAppName"
                value={rollbackAppName}
                onChange={(e) => setRollbackAppName(e.target.value)}
                placeholder="e.g., brain-backend"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="rollbackEnvironment">Environment</Label>
              <Input
                id="rollbackEnvironment"
                value={rollbackEnvironment}
                onChange={(e) => setRollbackEnvironment(e.target.value)}
                placeholder="e.g., production"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="backupId">Backup ID</Label>
            <Input
              id="backupId"
              value={backupId}
              onChange={(e) => setBackupId(e.target.value)}
              placeholder="e.g., backup_20231220_143022"
            />
            <p className="text-xs text-muted-foreground">
              Backup ID from pre-deployment snapshot
            </p>
          </div>

          <Button
            onClick={handleRollback}
            disabled={isRollingBack || !rollbackAppName || !rollbackEnvironment || !backupId}
            variant="destructive"
            className="w-full"
          >
            {isRollingBack ? "Rolling Back..." : "Rollback Deployment"}
          </Button>

          {rollbackDeployment.data && (
            <Alert className="border-green-500/50">
              <AlertDescription className="space-y-2">
                <div className="flex items-center gap-2 font-semibold text-green-500">
                  <CheckCircle2 className="w-4 h-4" />
                  Rollback Completed
                </div>
                <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                  {JSON.stringify(rollbackDeployment.data, null, 2)}
                </pre>
              </AlertDescription>
            </Alert>
          )}

          {rollbackDeployment.error && (
            <Alert className="border-red-500/50">
              <AlertDescription>
                <p className="text-red-500 font-semibold">Rollback Failed</p>
                <p className="text-sm">{rollbackDeployment.error.message}</p>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Deployment Workflow Info */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">Automated Deployment Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-500">
                1
              </div>
              <div>
                <p className="font-semibold">Risk Assessment</p>
                <p className="text-xs text-muted-foreground">
                  Environment-based risk: dev=LOW, staging=MEDIUM, production=CRITICAL
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-500">
                2
              </div>
              <div>
                <p className="font-semibold">Supervisor Approval (if needed)</p>
                <p className="text-xs text-muted-foreground">
                  Production deployments require human approval before proceeding
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-500">
                3
              </div>
              <div>
                <p className="font-semibold">Pre-deployment Checks</p>
                <p className="text-xs text-muted-foreground">
                  Version validation, dependency checks, environment verification
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-500">
                4
              </div>
              <div>
                <p className="font-semibold">Backup Creation</p>
                <p className="text-xs text-muted-foreground">
                  Automatic snapshot for rollback capability
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-500">
                5
              </div>
              <div>
                <p className="font-semibold">Deployment Execution</p>
                <p className="text-xs text-muted-foreground">
                  Safe deployment with progress monitoring
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-500">
                6
              </div>
              <div>
                <p className="font-semibold">Health Check & Auto-Rollback</p>
                <p className="text-xs text-muted-foreground">
                  Post-deployment health verification; automatic rollback on failure
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
