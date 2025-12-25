/**
 * SiteOverview Component
 *
 * Overview tab for site detail page
 * Shows manifest metadata, container info, and quick actions
 */

"use client";

import { useState } from "react";
import { Play, Square, RotateCcw, Trash2, Package, Container, Clock, Hash } from "lucide-react";
import type { SiteManifest, HealthStatus } from "@/types/webgenesis";
import {
  startSite,
  stopSite,
  restartSite,
  removeSite,
} from "@/lib/webgenesisApi";

interface SiteOverviewProps {
  siteId: string;
  manifest: SiteManifest;
  isRunning: boolean;
  healthStatus?: string;
  onRefresh?: () => void;
}

export function SiteOverview({
  siteId,
  manifest,
  isRunning,
  healthStatus,
  onRefresh,
}: SiteOverviewProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  async function handleAction(action: "start" | "stop" | "restart" | "remove") {
    setIsProcessing(true);
    try {
      switch (action) {
        case "start":
          await startSite(siteId);
          break;
        case "stop":
          await stopSite(siteId);
          break;
        case "restart":
          await restartSite(siteId);
          break;
        case "remove":
          if (
            confirm(
              `Are you sure you want to remove site ${siteId}? This will stop and remove the container.`
            )
          ) {
            await removeSite(siteId, false);
            // Redirect to sites list after removal
            window.location.href = "/webgenesis";
          } else {
            setIsProcessing(false);
            return;
          }
          break;
      }

      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error(`Failed to ${action} site:`, error);
      alert(`Failed to ${action} site: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Quick Actions */}
      <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
        <h2 className="mb-3 text-sm font-semibold text-white">Quick Actions</h2>
        <div className="flex flex-wrap gap-2">
          <ActionButton
            icon={Play}
            label="Start"
            onClick={() => handleAction("start")}
            disabled={isRunning || isProcessing}
            variant="success"
          />
          <ActionButton
            icon={Square}
            label="Stop"
            onClick={() => handleAction("stop")}
            disabled={!isRunning || isProcessing}
            variant="warning"
          />
          <ActionButton
            icon={RotateCcw}
            label="Restart"
            onClick={() => handleAction("restart")}
            disabled={!isRunning || isProcessing}
            variant="default"
          />
          <ActionButton
            icon={Trash2}
            label="Remove"
            onClick={() => handleAction("remove")}
            disabled={isProcessing}
            variant="danger"
          />
        </div>
      </section>

      {/* Site Metadata */}
      <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
        <h2 className="mb-3 text-sm font-semibold text-white">Site Information</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <MetadataItem
            icon={Hash}
            label="Site ID"
            value={manifest.site_id}
            mono
          />
          <MetadataItem
            icon={Hash}
            label="Spec Hash"
            value={manifest.spec_hash}
            mono
          />
          <MetadataItem
            icon={Clock}
            label="Created At"
            value={formatTimestamp(manifest.created_at)}
          />
          <MetadataItem
            icon={Clock}
            label="Updated At"
            value={formatTimestamp(manifest.updated_at)}
          />
          {manifest.generated_at && (
            <MetadataItem
              icon={Clock}
              label="Generated At"
              value={formatTimestamp(manifest.generated_at)}
            />
          )}
          {manifest.built_at && (
            <MetadataItem
              icon={Clock}
              label="Built At"
              value={formatTimestamp(manifest.built_at)}
            />
          )}
          {manifest.deployed_at && (
            <MetadataItem
              icon={Clock}
              label="Deployed At"
              value={formatTimestamp(manifest.deployed_at)}
            />
          )}
          {manifest.artifact_hash && (
            <MetadataItem
              icon={Package}
              label="Artifact Hash"
              value={manifest.artifact_hash}
              mono
            />
          )}
        </div>
      </section>

      {/* Container Info */}
      {manifest.docker_container_id && (
        <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
          <h2 className="mb-3 text-sm font-semibold text-white">Container Information</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <MetadataItem
              icon={Container}
              label="Container ID"
              value={manifest.docker_container_id}
              mono
            />
            {manifest.docker_image_tag && (
              <MetadataItem
                icon={Package}
                label="Image Tag"
                value={manifest.docker_image_tag}
                mono
              />
            )}
            {manifest.deployed_url && (
              <MetadataItem
                icon={Package}
                label="Deployed URL"
                value={
                  <a
                    href={manifest.deployed_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 hover:underline"
                  >
                    {manifest.deployed_url}
                  </a>
                }
              />
            )}
            {manifest.deployed_ports && manifest.deployed_ports.length > 0 && (
              <MetadataItem
                icon={Package}
                label="Ports"
                value={manifest.deployed_ports.join(", ")}
              />
            )}
            {manifest.deploy_path && (
              <MetadataItem
                icon={Package}
                label="Deploy Path"
                value={manifest.deploy_path}
                mono
              />
            )}
          </div>
        </section>
      )}

      {/* Error Info */}
      {manifest.last_error && (
        <section className="rounded-2xl border border-red-800 bg-red-900/20 p-4">
          <h2 className="mb-2 text-sm font-semibold text-red-500">Last Error</h2>
          <p className="text-sm text-neutral-300">{manifest.last_error}</p>
          <p className="mt-2 text-xs text-neutral-400">
            Error count: {manifest.error_count}
          </p>
        </section>
      )}

      {/* Metadata */}
      {manifest.metadata && Object.keys(manifest.metadata).length > 0 && (
        <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
          <h2 className="mb-3 text-sm font-semibold text-white">Additional Metadata</h2>
          <pre className="overflow-auto rounded-lg bg-neutral-950 p-3 text-xs text-neutral-300">
            {JSON.stringify(manifest.metadata, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

// ============================================================================
// Action Button Component
// ============================================================================

interface ActionButtonProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: "default" | "success" | "warning" | "danger";
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  disabled = false,
  variant = "default",
}: ActionButtonProps) {
  const variantClasses = {
    default: "bg-neutral-800 text-neutral-200 hover:bg-neutral-700",
    success: "bg-emerald-900/60 text-emerald-300 hover:bg-emerald-900/80",
    warning: "bg-amber-900/60 text-amber-300 hover:bg-amber-900/80",
    danger: "bg-rose-900/60 text-rose-300 hover:bg-rose-900/80",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]}`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

// ============================================================================
// Metadata Item Component
// ============================================================================

interface MetadataItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}

function MetadataItem({ icon: Icon, label, value, mono = false }: MetadataItemProps) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="h-5 w-5 text-neutral-500" />
      <div className="flex-1">
        <div className="text-xs font-medium text-neutral-400">{label}</div>
        <div className={`mt-1 text-sm text-neutral-200 ${mono ? "font-mono text-xs" : ""}`}>
          {value || <span className="text-neutral-500">—</span>}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}
