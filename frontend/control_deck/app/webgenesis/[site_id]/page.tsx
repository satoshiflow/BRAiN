"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Globe } from "lucide-react";
import { getSiteStatus } from "@/lib/webgenesisApi";
import type { SiteStatusResponse } from "@/types/webgenesis";
import { SiteStatusBadge } from "@/components/webgenesis/SiteStatusBadge";
import { LifecycleBadge } from "@/components/webgenesis/LifecycleBadge";
import { HealthBadge } from "@/components/webgenesis/HealthBadge";
import { SiteOverview } from "@/components/webgenesis/SiteOverview";
import { ReleaseList } from "@/components/webgenesis/ReleaseList";
import { DNSPanel } from "@/components/webgenesis/DNSPanel";
import { AuditTimeline } from "@/components/webgenesis/AuditTimeline";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

type Tab = "overview" | "releases" | "dns" | "audit";

interface PageProps {
  params: {
    site_id: string;
  };
}

export default function SiteDetailPage({ params }: PageProps) {
  const { site_id } = params;
  const [siteState, setSiteState] = useState<LoadState<SiteStatusResponse>>({
    loading: true,
  });
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  useEffect(() => {
    loadSiteStatus();
  }, [site_id]);

  async function loadSiteStatus() {
    setSiteState((prev) => ({ ...prev, loading: true, error: undefined }));
    try {
      const status = await getSiteStatus(site_id);
      setSiteState({ data: status, loading: false });
    } catch (err) {
      setSiteState({ loading: false, error: String(err) });
    }
  }

  if (siteState.loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-neutral-700 border-t-blue-500" />
          <span className="text-sm text-neutral-400">Loading site details...</span>
        </div>
      </div>
    );
  }

  if (siteState.error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md rounded-2xl border border-red-800 bg-red-900/20 p-6">
          <h3 className="text-lg font-semibold text-red-500">Error Loading Site</h3>
          <p className="mt-2 text-sm text-neutral-300">{siteState.error}</p>
          <Link
            href="/webgenesis"
            className="mt-4 inline-flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Sites
          </Link>
        </div>
      </div>
    );
  }

  const { manifest, is_running, health_status } = siteState.data!;

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <header className="flex flex-col gap-4">
        <Link
          href="/webgenesis"
          className="inline-flex w-fit items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-neutral-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Sites
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-blue-900/20 p-3">
              <Globe className="h-8 w-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">{site_id}</h1>
              <p className="mt-1 text-sm text-neutral-400">
                WebGenesis Site Details
              </p>
              <div className="mt-3 flex items-center gap-2">
                <SiteStatusBadge status={manifest.status} />
                {manifest.docker_container_id && (
                  <LifecycleBadge
                    status={is_running ? "running" : "stopped"}
                  />
                )}
                {health_status && <HealthBadge status={health_status} />}
              </div>
            </div>
          </div>

          {manifest.deployed_url && (
            <a
              href={manifest.deployed_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              Visit Site →
            </a>
          )}
        </div>
      </header>

      {/* Tabs */}
      <nav className="border-b border-neutral-800">
        <div className="flex gap-1">
          <TabButton
            label="Overview"
            isActive={activeTab === "overview"}
            onClick={() => setActiveTab("overview")}
          />
          <TabButton
            label="Releases"
            isActive={activeTab === "releases"}
            onClick={() => setActiveTab("releases")}
          />
          <TabButton
            label="DNS"
            isActive={activeTab === "dns"}
            onClick={() => setActiveTab("dns")}
          />
          <TabButton
            label="Audit"
            isActive={activeTab === "audit"}
            onClick={() => setActiveTab("audit")}
          />
        </div>
      </nav>

      {/* Tab Content */}
      <div className="flex-1">
        {activeTab === "overview" && (
          <SiteOverview
            siteId={site_id}
            manifest={manifest}
            isRunning={is_running}
            healthStatus={health_status}
            onRefresh={loadSiteStatus}
          />
        )}
        {activeTab === "releases" && (
          <ReleaseList siteId={site_id} onRefresh={loadSiteStatus} />
        )}
        {activeTab === "dns" && <DNSPanel siteId={site_id} />}
        {activeTab === "audit" && <AuditTimeline siteId={site_id} />}
      </div>
    </div>
  );
}

// ============================================================================
// Tab Button Component
// ============================================================================

interface TabButtonProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
}

function TabButton({ label, isActive, onClick }: TabButtonProps) {
  const baseClass =
    "px-4 py-2 text-sm font-medium transition-colors border-b-2";
  const activeClass = isActive
    ? "border-blue-500 text-blue-400"
    : "border-transparent text-neutral-400 hover:text-neutral-200";

  return (
    <button onClick={onClick} className={`${baseClass} ${activeClass}`}>
      {label}
    </button>
  );
}
