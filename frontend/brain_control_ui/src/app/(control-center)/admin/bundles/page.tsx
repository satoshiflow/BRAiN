/**
 * Bundles Management Page
 *
 * Comprehensive bundle management interface for offline model bundles.
 * Includes discovery, validation, loading, and quarantine management.
 *
 * @page admin/bundles
 * @version 1.0.0
 */

"use client";

import { useState } from "react";
import {
  Package,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
  RefreshCw,
  Play,
  Shield,
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
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import {
  useBundles,
  useBundleDiscover,
  useBundleLoad,
  useBundleValidate,
  useBundleRemoveQuarantine,
} from "@/hooks/useSovereignMode";
import { BundleStatus, type Bundle } from "@/types/sovereign";

/**
 * Get badge variant for bundle status
 */
function getStatusBadge(status: BundleStatus) {
  const configs = {
    [BundleStatus.PENDING]: {
      label: "Pending",
      variant: "secondary" as const,
      icon: AlertTriangle,
    },
    [BundleStatus.VALIDATED]: {
      label: "Validated",
      variant: "default" as const,
      icon: CheckCircle2,
    },
    [BundleStatus.LOADED]: {
      label: "Loaded",
      variant: "default" as const,
      icon: CheckCircle2,
    },
    [BundleStatus.QUARANTINED]: {
      label: "Quarantined",
      variant: "destructive" as const,
      icon: XCircle,
    },
    [BundleStatus.FAILED]: {
      label: "Failed",
      variant: "destructive" as const,
      icon: XCircle,
    },
  };

  const config = configs[status];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}

/**
 * Bundle Row Component
 */
function BundleRow({
  bundle,
  onValidate,
  onLoad,
  onRemoveQuarantine,
  isLoading,
}: {
  bundle: Bundle;
  onValidate: (id: string) => void;
  onLoad: (id: string) => void;
  onRemoveQuarantine: (id: string) => void;
  isLoading: boolean;
}) {
  const isLoaded = bundle.status === BundleStatus.LOADED;
  const isQuarantined = bundle.status === BundleStatus.QUARANTINED;

  return (
    <TableRow>
      <TableCell className="font-medium">
        <div className="flex flex-col">
          <span>{bundle.name}</span>
          <span className="text-xs text-muted-foreground">{bundle.id}</span>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="outline">{bundle.version}</Badge>
      </TableCell>
      <TableCell>
        <div className="flex flex-col">
          <span className="text-sm">{bundle.model_type}</span>
          <span className="text-xs text-muted-foreground">{bundle.model_size}</span>
        </div>
      </TableCell>
      <TableCell>{getStatusBadge(bundle.status)}</TableCell>
      <TableCell>
        {bundle.last_validated
          ? new Date(bundle.last_validated).toLocaleDateString()
          : "Never"}
      </TableCell>
      <TableCell>
        <span className="text-xs text-muted-foreground">{bundle.load_count}x</span>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {!isLoaded && !isQuarantined && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onValidate(bundle.id)}
                disabled={isLoading}
              >
                <Shield className="mr-1 h-3 w-3" />
                Validate
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => onLoad(bundle.id)}
                disabled={isLoading}
              >
                <Play className="mr-1 h-3 w-3" />
                Load
              </Button>
            </>
          )}

          {isQuarantined && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onRemoveQuarantine(bundle.id)}
              disabled={isLoading}
            >
              Remove Quarantine
            </Button>
          )}

          {isLoaded && (
            <Badge variant="default" className="bg-emerald-500">
              Active
            </Badge>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

/**
 * Main Bundles Page
 */
export default function BundlesPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const { data: bundles, isLoading, error } = useBundles();
  const discoverMutation = useBundleDiscover();
  const loadMutation = useBundleLoad();
  const validateMutation = useBundleValidate();
  const removeQuarantineMutation = useBundleRemoveQuarantine();

  const handleDiscover = () => {
    discoverMutation.mutate();
  };

  const handleValidate = (bundleId: string) => {
    validateMutation.mutate({ bundleId, force: true });
  };

  const handleLoad = (bundleId: string) => {
    loadMutation.mutate({
      bundle_id: bundleId,
      force_revalidate: true,
      skip_quarantine_check: false,
    });
  };

  const handleRemoveQuarantine = (bundleId: string) => {
    removeQuarantineMutation.mutate(bundleId);
  };

  // Filter bundles
  const filteredBundles =
    bundles?.filter(
      (b) =>
        b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.id.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

  const isAnyMutationPending =
    loadMutation.isPending ||
    validateMutation.isPending ||
    discoverMutation.isPending ||
    removeQuarantineMutation.isPending;

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">Loading bundles...</p>
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
          <AlertDescription>Failed to load bundles: {error.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Bundle Management</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage offline model bundles with validation and loading
          </p>
        </div>

        <Button onClick={handleDiscover} disabled={discoverMutation.isPending}>
          <RefreshCw className={cn("mr-2 h-4 w-4", discoverMutation.isPending && "animate-spin")} />
          Discover Bundles
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Total</p>
                <p className="text-2xl font-bold">{bundles?.length || 0}</p>
              </div>
              <Package className="h-5 w-5 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Validated</p>
                <p className="text-2xl font-bold">
                  {bundles?.filter((b) => b.status === BundleStatus.VALIDATED).length || 0}
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
                <p className="text-xs text-muted-foreground">Loaded</p>
                <p className="text-2xl font-bold">
                  {bundles?.filter((b) => b.status === BundleStatus.LOADED).length || 0}
                </p>
              </div>
              <Play className="h-5 w-5 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Quarantined</p>
                <p className="text-2xl font-bold">
                  {bundles?.filter((b) => b.status === BundleStatus.QUARANTINED).length || 0}
                </p>
              </div>
              <AlertTriangle className="h-5 w-5 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bundles Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Available Bundles</CardTitle>
              <CardDescription>All discovered offline model bundles</CardDescription>
            </div>

            <div className="relative w-64">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search bundles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredBundles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Package className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-sm font-medium">No bundles found</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Click &quot;Discover Bundles&quot; to scan for offline bundles
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bundle</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Validated</TableHead>
                  <TableHead>Loads</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBundles.map((bundle) => (
                  <BundleRow
                    key={bundle.id}
                    bundle={bundle}
                    onValidate={handleValidate}
                    onLoad={handleLoad}
                    onRemoveQuarantine={handleRemoveQuarantine}
                    isLoading={isAnyMutationPending}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
