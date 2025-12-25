/**
 * ReleaseList Component
 *
 * Releases tab for site detail page
 * Shows release history with rollback functionality
 */

"use client";

import { useEffect, useState } from "react";
import { History, RotateCcw, CheckCircle2, Package, Clock } from "lucide-react";
import type { ReleaseMetadata } from "@/types/webgenesis";
import { fetchReleases, rollbackSite } from "@/lib/webgenesisApi";
import { HealthBadge } from "./HealthBadge";
import { ConfirmModal } from "./ConfirmModal";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

interface ReleaseListProps {
  siteId: string;
  onRefresh?: () => void;
}

export function ReleaseList({ siteId, onRefresh }: ReleaseListProps) {
  const [releasesState, setReleasesState] = useState<LoadState<ReleaseMetadata[]>>({
    loading: true,
  });
  const [isRollingBack, setIsRollingBack] = useState<string | null>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [selectedReleaseId, setSelectedReleaseId] = useState<string | null>(null);

  useEffect(() => {
    loadReleases();
  }, [siteId]);

  async function loadReleases() {
    setReleasesState((prev) => ({ ...prev, loading: true, error: undefined }));
    try {
      const response = await fetchReleases(siteId);
      setReleasesState({ data: response.releases, loading: false });
    } catch (err) {
      setReleasesState({ loading: false, error: String(err) });
    }
  }

  function handleRollback(releaseId: string) {
    // Show confirmation modal instead of browser confirm
    setSelectedReleaseId(releaseId);
    setIsConfirmOpen(true);
  }

  async function handleRollbackConfirm() {
    if (!selectedReleaseId) return;

    setIsRollingBack(selectedReleaseId);
    try {
      await rollbackSite(siteId, selectedReleaseId);
      await loadReleases();
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error("Failed to rollback:", error);
      alert(`Failed to rollback: ${error}`);
    } finally {
      setIsRollingBack(null);
      setSelectedReleaseId(null);
    }
  }

  if (releasesState.loading) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8">
        <div className="flex items-center justify-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-neutral-700 border-t-blue-500" />
          <span className="text-sm text-neutral-400">Loading releases...</span>
        </div>
      </div>
    );
  }

  if (releasesState.error) {
    return (
      <div className="rounded-2xl border border-red-800 bg-red-900/20 p-4">
        <h3 className="text-sm font-semibold text-red-500">Error Loading Releases</h3>
        <p className="mt-1 text-sm text-neutral-300">{releasesState.error}</p>
      </div>
    );
  }

  const releases = releasesState.data ?? [];

  if (releases.length === 0) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8 text-center">
        <History className="mx-auto h-12 w-12 text-neutral-600" />
        <p className="mt-3 text-sm text-neutral-400">No releases found</p>
        <p className="mt-1 text-xs text-neutral-500">
          Deploy the site to create the first release
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Release History</h2>
          <p className="text-sm text-neutral-400">
            {releases.length} release{releases.length !== 1 ? "s" : ""} found
          </p>
        </div>
        <button
          onClick={loadReleases}
          className="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-200 transition-colors hover:bg-neutral-700"
        >
          Refresh
        </button>
      </div>

      <div className="flex flex-col gap-3">
        {releases.map((release, index) => (
          <ReleaseCard
            key={release.release_id}
            release={release}
            isLatest={index === 0}
            onRollback={() => handleRollback(release.release_id)}
            isRollingBack={isRollingBack === release.release_id}
          />
        ))}
      </div>

      <ConfirmModal
        isOpen={isConfirmOpen}
        onClose={() => {
          setIsConfirmOpen(false);
          setSelectedReleaseId(null);
        }}
        onConfirm={handleRollbackConfirm}
        title="Rollback to Release"
        message={
          selectedReleaseId
            ? `Are you sure you want to rollback to release ${selectedReleaseId.slice(0, 12)}?`
            : "Confirm rollback?"
        }
        confirmLabel="Rollback"
        variant="warning"
      />
    </div>
  );
}

// ============================================================================
// Release Card Component
// ============================================================================

interface ReleaseCardProps {
  release: ReleaseMetadata;
  isLatest: boolean;
  onRollback: () => void;
  isRollingBack: boolean;
}

function ReleaseCard({
  release,
  isLatest,
  onRollback,
  isRollingBack,
}: ReleaseCardProps) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-blue-900/20 p-2">
            <Package className="h-5 w-5 text-blue-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-mono text-sm font-medium text-white">
                {release.release_id}
              </h3>
              {isLatest && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-900/60 px-2 py-1 text-[10px] uppercase text-emerald-300">
                  <CheckCircle2 className="h-3 w-3" />
                  Latest
                </span>
              )}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-neutral-400">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatTimestamp(release.created_at)}
              </div>
              {release.artifact_hash && (
                <div className="flex items-center gap-1">
                  <Package className="h-3 w-3" />
                  <span className="font-mono">{release.artifact_hash.slice(0, 12)}...</span>
                </div>
              )}
              {release.health_status && (
                <HealthBadge status={release.health_status} />
              )}
            </div>
            {release.deployed_url && (
              <div className="mt-2">
                <a
                  href={release.deployed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-400 hover:text-blue-300 hover:underline"
                >
                  {release.deployed_url}
                </a>
              </div>
            )}
            {release.metadata && Object.keys(release.metadata).length > 0 && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-neutral-500 hover:text-neutral-400">
                  View metadata
                </summary>
                <pre className="mt-2 overflow-auto rounded-lg bg-neutral-950 p-2 text-xs text-neutral-300">
                  {JSON.stringify(release.metadata, null, 2)}
                </pre>
              </details>
            )}
          </div>
        </div>

        {!isLatest && (
          <button
            onClick={onRollback}
            disabled={isRollingBack}
            className="inline-flex items-center gap-2 rounded-lg bg-amber-900/60 px-3 py-1.5 text-xs font-medium text-amber-300 transition-colors hover:bg-amber-900/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RotateCcw className="h-3 w-3" />
            {isRollingBack ? "Rolling back..." : "Rollback"}
          </button>
        )}
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
    });
  } catch {
    return "—";
  }
}
