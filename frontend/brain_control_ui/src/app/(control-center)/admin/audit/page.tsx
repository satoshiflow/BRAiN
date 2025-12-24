/**
 * Audit Log Page
 *
 * Comprehensive audit trail for sovereign mode operations.
 * Displays mode changes, bundle operations, and security events.
 *
 * @page admin/audit
 * @version 1.0.0
 */

"use client";

import { useState } from "react";
import {
  ScrollText,
  CheckCircle2,
  XCircle,
  Filter,
  Download,
  AlertTriangle,
  Shield,
  Package,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { useAuditLog } from "@/hooks/useSovereignMode";
import type { AuditEntry } from "@/types/sovereign";

/**
 * Event type configuration
 */
const EVENT_TYPES = {
  mode_change: {
    label: "Mode Change",
    icon: Shield,
    color: "text-violet-500",
  },
  bundle_load: {
    label: "Bundle Load",
    icon: Package,
    color: "text-blue-500",
  },
  bundle_validation: {
    label: "Bundle Validation",
    icon: CheckCircle2,
    color: "text-emerald-500",
  },
  network_block: {
    label: "Network Block",
    icon: AlertTriangle,
    color: "text-amber-500",
  },
} as const;

/**
 * Get event type badge
 */
function getEventTypeBadge(eventType: string) {
  const config = EVENT_TYPES[eventType as keyof typeof EVENT_TYPES] || {
    label: eventType,
    icon: ScrollText,
    color: "text-gray-500",
  };

  const Icon = config.icon;

  return (
    <Badge variant="outline" className="gap-1">
      <Icon className={cn("h-3 w-3", config.color)} />
      {config.label}
    </Badge>
  );
}

/**
 * Audit Entry Row Component
 */
function AuditEntryRow({ entry }: { entry: AuditEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/30"
        onClick={() => setExpanded(!expanded)}
      >
        <TableCell className="font-mono text-xs">{entry.id.slice(0, 8)}</TableCell>
        <TableCell className="text-xs">
          {new Date(entry.timestamp).toLocaleString()}
        </TableCell>
        <TableCell>{getEventTypeBadge(entry.event_type)}</TableCell>
        <TableCell>
          <Badge variant={entry.success ? "default" : "destructive"} className="gap-1">
            {entry.success ? (
              <>
                <CheckCircle2 className="h-3 w-3" />
                Success
              </>
            ) : (
              <>
                <XCircle className="h-3 w-3" />
                Failed
              </>
            )}
          </Badge>
        </TableCell>
        <TableCell className="text-xs text-muted-foreground">{entry.triggered_by}</TableCell>
        <TableCell>
          <Button variant="ghost" size="sm">
            {expanded ? "Hide" : "Details"}
          </Button>
        </TableCell>
      </TableRow>

      {expanded && (
        <TableRow>
          <TableCell colSpan={6} className="bg-muted/20">
            <div className="space-y-3 p-4">
              {/* Reason */}
              {entry.reason && (
                <div>
                  <span className="text-xs font-semibold text-muted-foreground">Reason:</span>
                  <p className="mt-1 text-sm">{entry.reason}</p>
                </div>
              )}

              {/* Mode Change Details */}
              {entry.mode_before && entry.mode_after && (
                <div>
                  <span className="text-xs font-semibold text-muted-foreground">Mode Change:</span>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant="outline">{entry.mode_before}</Badge>
                    <span className="text-xs">→</span>
                    <Badge variant="outline">{entry.mode_after}</Badge>
                  </div>
                </div>
              )}

              {/* Bundle ID */}
              {entry.bundle_id && (
                <div>
                  <span className="text-xs font-semibold text-muted-foreground">Bundle:</span>
                  <p className="mt-1 font-mono text-sm">{entry.bundle_id}</p>
                </div>
              )}

              {/* Error */}
              {entry.error && (
                <div>
                  <span className="text-xs font-semibold text-red-500">Error:</span>
                  <p className="mt-1 text-sm text-red-500">{entry.error}</p>
                </div>
              )}

              {/* Metadata */}
              {Object.keys(entry.metadata).length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-muted-foreground">Metadata:</span>
                  <pre className="mt-1 overflow-x-auto rounded-lg bg-background p-3 text-xs">
                    {JSON.stringify(entry.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

/**
 * Main Audit Log Page
 */
export default function AuditLogPage() {
  const [limit, setLimit] = useState(100);
  const [eventTypeFilter, setEventTypeFilter] = useState<string | undefined>(undefined);

  const { data: entries, isLoading, error, refetch } = useAuditLog(limit, eventTypeFilter);

  const handleExport = () => {
    if (!entries) return;

    const dataStr = JSON.stringify(entries, null, 2);
    const dataUri = "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);

    const exportFileDefaultName = `audit-log-${new Date().toISOString()}.json`;

    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">Loading audit log...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <Alert variant="destructive" className="max-w-md">
          <XCircle className="h-4 w-4" />
          <AlertDescription>Failed to load audit log: {error.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Comprehensive operation history and security events
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={!entries || entries.length === 0}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Total Entries</p>
                <p className="text-2xl font-bold">{entries?.length || 0}</p>
              </div>
              <ScrollText className="h-5 w-5 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Successful</p>
                <p className="text-2xl font-bold">
                  {entries?.filter((e) => e.success).length || 0}
                </p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Failed</p>
                <p className="text-2xl font-bold">
                  {entries?.filter((e) => !e.success).length || 0}
                </p>
              </div>
              <XCircle className="h-5 w-5 text-red-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Mode Changes</p>
                <p className="text-2xl font-bold">
                  {entries?.filter((e) => e.event_type === "mode_change").length || 0}
                </p>
              </div>
              <Shield className="h-5 w-5 text-violet-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Audit Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Audit Entries</CardTitle>
              <CardDescription>Click on entries to view details</CardDescription>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select
                  value={eventTypeFilter || "all"}
                  onValueChange={(value) => setEventTypeFilter(value === "all" ? undefined : value)}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Filter by type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Events</SelectItem>
                    <SelectItem value="mode_change">Mode Changes</SelectItem>
                    <SelectItem value="bundle_load">Bundle Loads</SelectItem>
                    <SelectItem value="bundle_validation">Validations</SelectItem>
                    <SelectItem value="network_block">Network Blocks</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Select value={limit.toString()} onValueChange={(value) => setLimit(parseInt(value))}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="50">50 entries</SelectItem>
                  <SelectItem value="100">100 entries</SelectItem>
                  <SelectItem value="250">250 entries</SelectItem>
                  <SelectItem value="500">500 entries</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {!entries || entries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <ScrollText className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-sm font-medium">No audit entries found</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Audit events will appear here as they occur
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Triggered By</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => (
                  <AuditEntryRow key={entry.id} entry={entry} />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
