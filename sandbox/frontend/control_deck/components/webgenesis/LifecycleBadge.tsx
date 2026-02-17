/**
 * LifecycleBadge Component
 *
 * Displays lifecycle status with color coding
 * Matches SiteLifecycleStatus enum from types/webgenesis.ts
 */

import type { SiteLifecycleStatus } from "@/types/webgenesis";

interface LifecycleBadgeProps {
  status: SiteLifecycleStatus;
}

export function LifecycleBadge({ status }: LifecycleBadgeProps) {
  let className = "bg-slate-800 text-slate-100";

  switch (status) {
    case "running":
      className = "bg-emerald-900/60 text-emerald-300";
      break;
    case "stopped":
      className = "bg-slate-800 text-slate-300";
      break;
    case "exited":
      className = "bg-orange-900/60 text-orange-300";
      break;
    case "restarting":
      className = "bg-blue-900/60 text-blue-300";
      break;
    case "paused":
      className = "bg-amber-900/60 text-amber-300";
      break;
    case "dead":
      className = "bg-rose-900/60 text-rose-300";
      break;
    case "created":
      className = "bg-cyan-900/60 text-cyan-300";
      break;
    case "unknown":
      className = "bg-slate-700 text-slate-400";
      break;
  }

  return (
    <span className={`rounded-full px-2 py-1 text-[10px] uppercase ${className}`}>
      {status}
    </span>
  );
}
