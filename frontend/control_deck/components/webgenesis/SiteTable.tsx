/**
 * SiteTable Component
 *
 * Main data table for WebGenesis sites
 * Displays site list with status, lifecycle, health, and actions
 */

"use client";

import Link from "next/link";
import { ExternalLink, Globe, CheckCircle2, XCircle } from "lucide-react";
import type { SiteListItem } from "@/types/webgenesis";
import { SiteStatusBadge } from "./SiteStatusBadge";
import { LifecycleBadge } from "./LifecycleBadge";
import { HealthBadge } from "./HealthBadge";
import { SiteActions } from "./SiteActions";

interface SiteTableProps {
  sites: SiteListItem[];
  onRefresh?: () => void;
}

export function SiteTable({ sites, onRefresh }: SiteTableProps) {
  if (!sites.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center">
        <Globe className="mx-auto h-12 w-12 text-slate-600" />
        <p className="mt-3 text-sm text-slate-400">No sites found</p>
        <p className="mt-1 text-xs text-slate-500">
          Create your first site using the "Create New Site" button above
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/80">
      <div className="max-h-[600px] overflow-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="sticky top-0 bg-slate-900">
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="px-3 py-2 font-medium">Site ID</th>
              <th className="px-3 py-2 font-medium">Domain</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Lifecycle</th>
              <th className="px-3 py-2 font-medium">Health</th>
              <th className="px-3 py-2 font-medium">Release</th>
              <th className="px-3 py-2 font-medium">DNS</th>
              <th className="px-3 py-2 font-medium">URL</th>
              <th className="px-3 py-2 font-medium">Updated</th>
              <th className="px-3 py-2 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sites.map((site) => (
              <tr
                key={site.site_id}
                className="border-b border-slate-900/60 text-slate-200 hover:bg-slate-900/80"
              >
                {/* Site ID - Clickable link to detail page */}
                <td className="px-3 py-2">
                  <Link
                    href={`/webgenesis/${site.site_id}`}
                    className="font-mono text-[11px] text-blue-400 hover:text-blue-300 hover:underline"
                  >
                    {site.site_id.slice(0, 12)}…
                  </Link>
                </td>

                {/* Domain */}
                <td className="px-3 py-2 text-slate-200">
                  {site.domain || (
                    <span className="text-slate-500">—</span>
                  )}
                </td>

                {/* Status */}
                <td className="px-3 py-2">
                  <SiteStatusBadge status={site.status} />
                </td>

                {/* Lifecycle Status */}
                <td className="px-3 py-2">
                  {site.lifecycle_status ? (
                    <LifecycleBadge status={site.lifecycle_status} />
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>

                {/* Health Status */}
                <td className="px-3 py-2">
                  {site.health_status ? (
                    <HealthBadge status={site.health_status} />
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>

                {/* Current Release */}
                <td className="px-3 py-2">
                  {site.current_release_id ? (
                    <span className="font-mono text-[10px] text-slate-400">
                      {site.current_release_id.slice(0, 8)}…
                    </span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>

                {/* DNS Enabled */}
                <td className="px-3 py-2">
                  {site.dns_enabled ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <XCircle className="h-4 w-4 text-slate-600" />
                  )}
                </td>

                {/* Deployed URL */}
                <td className="px-3 py-2">
                  {site.deployed_url ? (
                    <a
                      href={site.deployed_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span className="text-[10px]">Open</span>
                    </a>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>

                {/* Updated At */}
                <td className="px-3 py-2 font-mono text-[11px] text-slate-400">
                  {formatTimestamp(site.updated_at)}
                </td>

                {/* Actions */}
                <td className="px-3 py-2 text-right">
                  <SiteActions site={site} onRefresh={onRefresh} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}
