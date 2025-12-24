/**
 * Network & Gates Status Page
 *
 * Monitors network connectivity and network guard status.
 * Displays configuration and blocked requests.
 *
 * @page admin/network
 * @version 1.0.0
 */

"use client";

import { Globe, Shield, AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

import {
  useSovereignStatus,
  useNetworkCheck,
  useSovereignConfig,
} from "@/hooks/useSovereignMode";

/**
 * Network Status Card
 */
function NetworkStatusCard({ isOnline, lastCheck }: { isOnline: boolean; lastCheck?: string | null }) {
  return (
    <Card className={cn("border-2", isOnline ? "border-emerald-500/30" : "border-amber-500/30")}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className={cn("h-5 w-5", isOnline ? "text-emerald-500" : "text-amber-500")} />
          Network Connectivity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Badge variant={isOnline ? "default" : "secondary"} className="gap-1">
              {isOnline ? (
                <>
                  <CheckCircle2 className="h-3 w-3" />
                  Online
                </>
              ) : (
                <>
                  <AlertTriangle className="h-3 w-3" />
                  Offline
                </>
              )}
            </Badge>
          </div>

          {lastCheck && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Last Check</span>
              <span className="text-sm">{new Date(lastCheck).toLocaleString()}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Network Guards Card
 */
function NetworkGuardsCard({
  blocksCount,
  blockHttp,
  blockDns,
  allowedDomains,
}: {
  blocksCount: number;
  blockHttp: boolean;
  blockDns: boolean;
  allowedDomains: string[];
}) {
  return (
    <Card className="border-2 border-violet-500/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-violet-500" />
          Network Guards
        </CardTitle>
        <CardDescription>Request blocking and whitelisting</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total Blocks</span>
            <Badge variant="secondary">{blocksCount}</Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Block External HTTP</span>
            <Badge variant={blockHttp ? "default" : "secondary"}>
              {blockHttp ? "Enabled" : "Disabled"}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Block External DNS</span>
            <Badge variant={blockDns ? "default" : "secondary"}>
              {blockDns ? "Enabled" : "Disabled"}
            </Badge>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Allowed Domains</span>
            <div className="flex flex-wrap gap-2">
              {allowedDomains.length > 0 ? (
                allowedDomains.map((domain) => (
                  <Badge key={domain} variant="outline" className="text-xs">
                    {domain}
                  </Badge>
                ))
              ) : (
                <span className="text-xs text-muted-foreground">No domains whitelisted</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Auto-Detection Card
 */
function AutoDetectionCard({
  enabled,
  interval,
  autoSwitch,
}: {
  enabled: boolean;
  interval: number;
  autoSwitch: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5" />
          Auto-Detection
        </CardTitle>
        <CardDescription>Automatic network monitoring</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Network Monitoring</span>
            <Badge variant={enabled ? "default" : "secondary"}>
              {enabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Check Interval</span>
            <span className="text-sm">{interval}s</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Auto-Switch Mode</span>
            <Badge variant={autoSwitch ? "default" : "secondary"}>
              {autoSwitch ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Main Network & Gates Page
 */
export default function NetworkPage() {
  const { data: status, isLoading: statusLoading } = useSovereignStatus();
  const { data: networkCheck, isLoading: networkLoading, refetch: refetchNetwork } = useNetworkCheck();
  const { data: config, isLoading: configLoading } = useSovereignConfig();

  const isLoading = statusLoading || networkLoading || configLoading;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">Loading network status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Network & Gates</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor network connectivity and security guards
          </p>
        </div>

        <Button onClick={() => refetchNetwork()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh Status
        </Button>
      </div>

      {/* Offline Warning */}
      {!status?.is_online && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Network connectivity is offline. System is operating in offline mode.
          </AlertDescription>
        </Alert>
      )}

      {/* Status Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <NetworkStatusCard
          isOnline={status?.is_online ?? false}
          lastCheck={status?.last_network_check}
        />

        <NetworkGuardsCard
          blocksCount={status?.network_blocks_count ?? 0}
          blockHttp={config?.block_external_http ?? false}
          blockDns={config?.block_external_dns ?? false}
          allowedDomains={config?.allowed_domains ?? []}
        />

        <AutoDetectionCard
          enabled={config?.network_check_enabled ?? false}
          interval={config?.network_check_interval ?? 30}
          autoSwitch={config?.auto_detect_network ?? false}
        />
      </div>

      {/* Network Check Details */}
      {networkCheck && (
        <Card>
          <CardHeader>
            <CardTitle>Latest Network Check</CardTitle>
            <CardDescription>Most recent connectivity verification</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <span className="text-xs text-muted-foreground">Result</span>
                <p className="text-sm font-medium">
                  {networkCheck.is_online ? "Online" : "Offline"}
                </p>
              </div>

              <div>
                <span className="text-xs text-muted-foreground">Method</span>
                <p className="text-sm font-medium">{networkCheck.check_method}</p>
              </div>

              {networkCheck.latency_ms !== null && (
                <div>
                  <span className="text-xs text-muted-foreground">Latency</span>
                  <p className="text-sm font-medium">{networkCheck.latency_ms.toFixed(2)} ms</p>
                </div>
              )}

              <div>
                <span className="text-xs text-muted-foreground">Checked At</span>
                <p className="text-sm font-medium">
                  {new Date(networkCheck.checked_at).toLocaleTimeString()}
                </p>
              </div>

              {networkCheck.error && (
                <div className="col-span-full">
                  <span className="text-xs text-muted-foreground">Error</span>
                  <p className="text-sm text-red-500">{networkCheck.error}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
