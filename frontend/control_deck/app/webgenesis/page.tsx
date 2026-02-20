"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Globe, Plus, AlertCircle } from "lucide-react";
import { fetchAllSites } from "@/lib/webgenesisApi";
import type { SiteListItem } from "@/types/webgenesis";

import { SiteTable } from "@/components/webgenesis/SiteTable";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function WebGenesisPage() {
  const [sitesState, setSitesState] = useState<LoadState<SiteListItem[]>>({
    loading: true,
  });

  useEffect(() => {
    loadSites();
  }, []);

  async function loadSites() {
    setSitesState((prev) => ({ ...prev, loading: true, error: undefined }));
    try {
      const sites = await fetchAllSites();
      setSitesState({ data: sites, loading: false });
    } catch (err) {
      setSitesState({
        loading: false,
        error: String(err),
      });
    }
  }

  // Calculate stats
  const sites = sitesState.data ?? [];
  const stats = {
    total: sites.length,
    running: sites.filter((s) => s.lifecycle_status === "running").length,
    stopped: sites.filter((s) => s.lifecycle_status === "stopped").length,
    failed: sites.filter((s) => s.status === "failed").length,
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <header className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Globe className="h-8 w-8 text-blue-500" />
            <h1 className="text-2xl font-semibold text-white">WebGenesis</h1>
          </div>
          <Link
            href="/webgenesis/new"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Create New Site
          </Link>
        </div>
        <p className="text-sm text-neutral-400">
          Website generation, deployment, and lifecycle management
        </p>
      </header>

      {/* Stats Cards */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatsCard label="Total Sites" value={stats.total} />
        <StatsCard label="Running" value={stats.running} tone="success" />
        <StatsCard label="Stopped" value={stats.stopped} tone="warning" />
        <StatsCard label="Failed" value={stats.failed} tone="danger" />
      </section>

      {/* Backend Endpoint Notice */}
      {!sitesState.loading && sites.length === 0 && !sitesState.error && (
        <div className="rounded-2xl border border-yellow-800 bg-yellow-900/20 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-500">
                Backend Endpoint Required
              </h3>
              <p className="mt-1 text-sm text-neutral-300">
                The site list endpoint <code className="px-1 py-0.5 bg-neutral-800 rounded text-yellow-400">GET /api/webgenesis/sites</code> is not yet implemented.
              </p>
              <p className="mt-2 text-sm text-neutral-400">
                To enable the site list view, add a backend endpoint that scans the WebGenesis storage directory and returns all sites with their status.
              </p>
              <p className="mt-2 text-sm text-neutral-400">
                For now, you can create new sites using the "Create New Site" button above, and access them directly via their site_id.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {sitesState.error && (
        <div className="rounded-2xl border border-red-800 bg-red-900/20 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-red-500">Error Loading Sites</h3>
              <p className="mt-1 text-sm text-neutral-300">{sitesState.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Sites Table */}
      {sitesState.loading ? (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8">
          <div className="flex items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-neutral-700 border-t-blue-500" />
            <span className="ml-3 text-sm text-neutral-400">Loading sites...</span>
          </div>
        </div>
      ) : sites.length > 0 ? (
        <section>
          <SiteTable sites={sites} onRefresh={loadSites} />
        </section>
      ) : null}

      {/* Quick Actions */}
      <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
        <h2 className="text-sm font-semibold text-white mb-3">Quick Start</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <QuickActionCard
            title="Create New Site"
            description="Use the WebsiteSpec Builder to create a new static website"
            href="/webgenesis/new"
          />
          <QuickActionCard
            title="Documentation"
            description="View WebGenesis operational and DNS integration guides"
            href="/docs/webgenesis"
          />
          <QuickActionCard
            title="System Settings"
            description="Configure WebGenesis, DNS, and trust tier settings"
            href="/settings"
          />
        </div>
      </section>
    </div>
  );
}

// ============================================================================
// Stats Card Component
// ============================================================================

function StatsCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "success" | "warning" | "danger" | "info";
}) {
  const toneColors = {
    success: "text-green-400",
    warning: "text-yellow-400",
    danger: "text-red-400",
    info: "text-blue-400",
  };

  const textColor = tone ? toneColors[tone] : "text-neutral-200";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
      <div className="text-xs font-medium text-neutral-400">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${textColor}`}>{value}</div>
    </div>
  );
}

// ============================================================================
// Quick Action Card Component
// ============================================================================

function QuickActionCard({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 transition-all hover:border-neutral-700 hover:bg-neutral-900"
    >
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <p className="mt-1 text-xs text-neutral-400">{description}</p>
    </Link>
  );
}
