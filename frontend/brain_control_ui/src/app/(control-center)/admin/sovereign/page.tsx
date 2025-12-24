/**
 * Sovereign Mode Control Page
 *
 * Main control interface for BRAiN Sovereign Mode operations.
 * Provides mode switching, status monitoring, and bundle management overview.
 *
 * @page admin/sovereign
 * @version 1.0.0
 */

"use client";

import { useState } from "react";
import { Shield, AlertTriangle, CheckCircle2, XCircle, Globe, Package } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

import { useSovereignStatus, useModeChange } from "@/hooks/useSovereignMode";
import { OperationMode, type ModeChangeRequest } from "@/types/sovereign";

/**
 * Get display configuration for operation mode
 */
function getModeConfig(mode: OperationMode) {
  const configs = {
    [OperationMode.ONLINE]: {
      label: "Online",
      color: "bg-emerald-500",
      textColor: "text-emerald-500",
      icon: Globe,
      description: "Full internet access, external models allowed",
    },
    [OperationMode.OFFLINE]: {
      label: "Offline",
      color: "bg-amber-500",
      textColor: "text-amber-500",
      icon: Package,
      description: "No internet, offline bundles only",
    },
    [OperationMode.SOVEREIGN]: {
      label: "Sovereign",
      color: "bg-violet-500",
      textColor: "text-violet-500",
      icon: Shield,
      description: "Strict mode with enhanced validation",
    },
    [OperationMode.QUARANTINE]: {
      label: "Quarantine",
      color: "bg-red-500",
      textColor: "text-red-500",
      icon: AlertTriangle,
      description: "Isolated mode, all external access blocked",
    },
  };

  return configs[mode];
}

/**
 * KPI Card Component
 */
function KPICard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  variant?: "default" | "success" | "warning" | "danger";
}) {
  const variantClasses = {
    default: "border-border",
    success: "border-emerald-500/30 bg-emerald-500/5",
    warning: "border-amber-500/30 bg-amber-500/5",
    danger: "border-red-500/30 bg-red-500/5",
  };

  return (
    <Card className={cn("border-2", variantClasses[variant])}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">
              {title}
            </p>
            <p className="mt-1 text-2xl font-bold">{value}</p>
            {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className="rounded-xl bg-muted/50 p-2">
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Mode Change Dialog Component
 */
function ModeChangeDialog({
  open,
  onOpenChange,
  currentMode,
  targetMode,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentMode: OperationMode;
  targetMode: OperationMode | null;
  onConfirm: (request: ModeChangeRequest) => void;
  isLoading: boolean;
}) {
  const [reason, setReason] = useState("");

  if (!targetMode) return null;

  const targetConfig = getModeConfig(targetMode);
  const currentConfig = getModeConfig(currentMode);

  const handleConfirm = () => {
    onConfirm({
      target_mode: targetMode,
      reason: reason || undefined,
      force: false,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Confirm Mode Change
          </DialogTitle>
          <DialogDescription>
            You are about to switch operation modes. This action will affect system behavior.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Mode Transition */}
          <div className="flex items-center justify-between rounded-lg border bg-muted/30 p-4">
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground">Current Mode</span>
              <span className="font-semibold">{currentConfig.label}</span>
            </div>
            <div className="text-muted-foreground">→</div>
            <div className="flex flex-col text-right">
              <span className="text-xs text-muted-foreground">Target Mode</span>
              <span className={cn("font-semibold", targetConfig.textColor)}>
                {targetConfig.label}
              </span>
            </div>
          </div>

          {/* Warnings */}
          {targetMode === OperationMode.SOVEREIGN && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Sovereign mode enables strict validation and blocks all external network access.
                Ensure you have a validated offline bundle loaded.
              </AlertDescription>
            </Alert>
          )}

          {targetMode === OperationMode.QUARANTINE && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Quarantine mode isolates the system completely. Only use this in emergency
                situations.
              </AlertDescription>
            </Alert>
          )}

          {/* Reason Input */}
          <div className="space-y-2">
            <Label htmlFor="reason" className="text-xs">
              Reason (Optional)
            </Label>
            <input
              id="reason"
              type="text"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
              placeholder="Why are you changing modes?"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isLoading}>
            {isLoading ? "Switching..." : "Confirm Change"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Main Sovereign Mode Page
 */
export default function SovereignModePage() {
  const { data: status, isLoading, error } = useSovereignStatus();
  const modeChangeMutation = useModeChange();

  const [modeDialogOpen, setModeDialogOpen] = useState(false);
  const [targetMode, setTargetMode] = useState<OperationMode | null>(null);

  const openModeDialog = (mode: OperationMode) => {
    setTargetMode(mode);
    setModeDialogOpen(true);
  };

  const handleModeChange = (request: ModeChangeRequest) => {
    modeChangeMutation.mutate(request, {
      onSuccess: () => {
        setModeDialogOpen(false);
        setTargetMode(null);
      },
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">Loading sovereign mode status...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !status) {
    return (
      <div className="flex h-full items-center justify-center">
        <Alert variant="destructive" className="max-w-md">
          <XCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load sovereign mode status: {error?.message || "Unknown error"}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const currentModeConfig = getModeConfig(status.mode);
  const ModeIcon = currentModeConfig.icon;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sovereign Mode</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Secure offline operation with model bundle management
          </p>
        </div>

        <Badge
          variant="outline"
          className={cn("gap-2 border-2 px-4 py-2", currentModeConfig.textColor)}
        >
          <ModeIcon className="h-4 w-4" />
          <span className="font-semibold">{currentModeConfig.label} Mode</span>
        </Badge>
      </div>

      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Network Status"
          value={status.is_online ? "Online" : "Offline"}
          subtitle={status.last_network_check ? `Checked at ${new Date(status.last_network_check).toLocaleTimeString()}` : undefined}
          icon={Globe}
          variant={status.is_online ? "success" : "warning"}
        />

        <KPICard
          title="Active Bundle"
          value={status.active_bundle?.name || "None"}
          subtitle={status.active_bundle?.version}
          icon={Package}
          variant={status.active_bundle ? "success" : "default"}
        />

        <KPICard
          title="Available Bundles"
          value={status.available_bundles}
          subtitle={`${status.validated_bundles} validated`}
          icon={CheckCircle2}
          variant="default"
        />

        <KPICard
          title="Network Blocks"
          value={status.network_blocks_count}
          subtitle="Total requests blocked"
          icon={Shield}
          variant={status.network_blocks_count > 0 ? "warning" : "default"}
        />
      </div>

      {/* Mode Control */}
      <Card>
        <CardHeader>
          <CardTitle>Operation Mode</CardTitle>
          <CardDescription>Switch between different operation modes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {Object.values(OperationMode).map((mode) => {
              const config = getModeConfig(mode);
              const Icon = config.icon;
              const isActive = status.mode === mode;

              return (
                <button
                  key={mode}
                  onClick={() => !isActive && openModeDialog(mode)}
                  disabled={isActive || modeChangeMutation.isPending}
                  className={cn(
                    "flex flex-col gap-3 rounded-xl border-2 p-4 text-left transition-all",
                    isActive
                      ? `${config.color} text-white shadow-lg`
                      : "border-border hover:border-foreground/20 hover:bg-muted/30",
                    isActive && "cursor-default",
                    !isActive && "cursor-pointer"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <Icon className={cn("h-6 w-6", isActive ? "text-white" : config.textColor)} />
                    {isActive && <CheckCircle2 className="h-4 w-4 text-white" />}
                  </div>
                  <div>
                    <div className="font-semibold">{config.label}</div>
                    <div
                      className={cn(
                        "mt-1 text-xs",
                        isActive ? "text-white/80" : "text-muted-foreground"
                      )}
                    >
                      {config.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Quarantine Warning */}
      {status.quarantined_bundles > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {status.quarantined_bundles} bundle(s) are quarantined. Review them in the Bundles
            section.
          </AlertDescription>
        </Alert>
      )}

      {/* Mode Change Dialog */}
      <ModeChangeDialog
        open={modeDialogOpen}
        onOpenChange={setModeDialogOpen}
        currentMode={status.mode}
        targetMode={targetMode}
        onConfirm={handleModeChange}
        isLoading={modeChangeMutation.isPending}
      />
    </div>
  );
}
