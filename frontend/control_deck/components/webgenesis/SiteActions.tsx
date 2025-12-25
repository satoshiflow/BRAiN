/**
 * SiteActions Component
 *
 * Action dropdown for site lifecycle operations
 * Uses shadcn/ui dropdown menu component
 */

"use client";

import { useState } from "react";
import { MoreVertical, Play, Square, RotateCcw, History, Trash2 } from "lucide-react";
import type { SiteListItem } from "@/types/webgenesis";
import {
  startSite,
  stopSite,
  restartSite,
  rollbackSite,
  removeSite,
} from "@/lib/webgenesisApi";

interface SiteActionsProps {
  site: SiteListItem;
  onRefresh?: () => void;
}

export function SiteActions({ site, onRefresh }: SiteActionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  async function handleAction(
    action: "start" | "stop" | "restart" | "rollback" | "remove"
  ) {
    setIsProcessing(true);
    try {
      switch (action) {
        case "start":
          await startSite(site.site_id);
          break;
        case "stop":
          await stopSite(site.site_id);
          break;
        case "restart":
          await restartSite(site.site_id);
          break;
        case "rollback":
          // Rollback to previous release (no specific release_id)
          await rollbackSite(site.site_id);
          break;
        case "remove":
          if (
            confirm(
              `Are you sure you want to remove site ${site.site_id}? This will stop and remove the container and optionally delete site data.`
            )
          ) {
            await removeSite(site.site_id, false); // keep_data = false by default
          } else {
            setIsProcessing(false);
            return;
          }
          break;
      }

      // Refresh site list after action
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error(`Failed to ${action} site:`, error);
      alert(`Failed to ${action} site: ${error}`);
    } finally {
      setIsProcessing(false);
      setIsOpen(false);
    }
  }

  const canStart = site.lifecycle_status === "stopped" || site.lifecycle_status === "exited";
  const canStop = site.lifecycle_status === "running";
  const canRestart = site.lifecycle_status === "running";
  const canRollback = site.current_release_id !== undefined;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isProcessing}
        className="rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200 disabled:opacity-50"
        aria-label="Site actions"
      >
        <MoreVertical className="h-4 w-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 z-10 mt-1 w-48 rounded-lg border border-slate-800 bg-slate-950 shadow-lg">
          <div className="py-1">
            <ActionButton
              icon={Play}
              label="Start"
              onClick={() => handleAction("start")}
              disabled={!canStart || isProcessing}
            />
            <ActionButton
              icon={Square}
              label="Stop"
              onClick={() => handleAction("stop")}
              disabled={!canStop || isProcessing}
            />
            <ActionButton
              icon={RotateCcw}
              label="Restart"
              onClick={() => handleAction("restart")}
              disabled={!canRestart || isProcessing}
            />
            <ActionButton
              icon={History}
              label="Rollback"
              onClick={() => handleAction("rollback")}
              disabled={!canRollback || isProcessing}
            />
            <div className="my-1 border-t border-slate-800" />
            <ActionButton
              icon={Trash2}
              label="Remove"
              onClick={() => handleAction("remove")}
              disabled={isProcessing}
              variant="danger"
            />
          </div>
        </div>
      )}
    </div>
  );
}

interface ActionButtonProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: "default" | "danger";
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  disabled = false,
  variant = "default",
}: ActionButtonProps) {
  const baseClass =
    "flex w-full items-center gap-2 px-4 py-2 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const variantClass =
    variant === "danger"
      ? "text-rose-400 hover:bg-rose-900/20 hover:text-rose-300"
      : "text-slate-300 hover:bg-slate-800 hover:text-slate-100";

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseClass} ${variantClass}`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}
