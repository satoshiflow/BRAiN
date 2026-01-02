/**
 * HealthBadge Component
 *
 * Displays health status with color coding and icons
 * Matches HealthStatus enum from types/webgenesis.ts
 */

import { CheckCircle2, XCircle, Clock, HelpCircle } from "lucide-react";
import type { HealthStatus } from "@/types/webgenesis";

interface HealthBadgeProps {
  status: HealthStatus;
}

export function HealthBadge({ status }: HealthBadgeProps) {
  let className = "bg-slate-800 text-slate-100";
  let Icon = HelpCircle;

  switch (status) {
    case "healthy":
      className = "bg-emerald-900/60 text-emerald-300";
      Icon = CheckCircle2;
      break;
    case "unhealthy":
      className = "bg-rose-900/60 text-rose-300";
      Icon = XCircle;
      break;
    case "starting":
      className = "bg-amber-900/60 text-amber-300";
      Icon = Clock;
      break;
    case "unknown":
      className = "bg-slate-800 text-slate-300";
      Icon = HelpCircle;
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] uppercase ${className}`}
    >
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}
