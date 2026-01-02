/**
 * SiteStatusBadge Component
 *
 * Displays the site status with color coding
 * Matches SiteStatus enum from types/webgenesis.ts
 */

import type { SiteStatus } from "@/types/webgenesis";

interface SiteStatusBadgeProps {
  status: SiteStatus;
}

export function SiteStatusBadge({ status }: SiteStatusBadgeProps) {
  let className = "bg-slate-800 text-slate-100";

  switch (status) {
    case "pending":
      className = "bg-slate-800 text-slate-300";
      break;
    case "generating":
      className = "bg-blue-900/60 text-blue-300";
      break;
    case "generated":
      className = "bg-cyan-900/60 text-cyan-300";
      break;
    case "building":
      className = "bg-purple-900/60 text-purple-300";
      break;
    case "built":
      className = "bg-indigo-900/60 text-indigo-300";
      break;
    case "deploying":
      className = "bg-amber-900/60 text-amber-300";
      break;
    case "deployed":
      className = "bg-emerald-900/60 text-emerald-300";
      break;
    case "failed":
      className = "bg-rose-900/60 text-rose-300";
      break;
  }

  return (
    <span className={`rounded-full px-2 py-1 text-[10px] uppercase ${className}`}>
      {status}
    </span>
  );
}
