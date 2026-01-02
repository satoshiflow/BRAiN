/**
 * AuditTimeline Component
 *
 * Audit tab for site detail page
 * Shows audit event timeline for the site
 */

"use client";

import { useEffect, useState } from "react";
import { Clock, AlertCircle, Info, AlertTriangle, XCircle } from "lucide-react";
import type { AuditEvent } from "@/types/webgenesis";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

interface AuditTimelineProps {
  siteId: string;
}

export function AuditTimeline({ siteId }: AuditTimelineProps) {
  const [eventsState, setEventsState] = useState<LoadState<AuditEvent[]>>({
    loading: true,
  });

  useEffect(() => {
    loadAuditEvents();
  }, [siteId]);

  async function loadAuditEvents() {
    setEventsState((prev) => ({ ...prev, loading: true, error: undefined }));

    // Placeholder - backend endpoint not yet implemented
    // TODO: Replace with actual API call when endpoint is ready
    // const response = await fetchAuditEvents(siteId);

    // Simulating empty response for now
    setTimeout(() => {
      setEventsState({
        data: [],
        loading: false,
      });
    }, 500);
  }

  if (eventsState.loading) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8">
        <div className="flex items-center justify-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-neutral-700 border-t-blue-500" />
          <span className="text-sm text-neutral-400">Loading audit events...</span>
        </div>
      </div>
    );
  }

  if (eventsState.error) {
    return (
      <div className="rounded-2xl border border-red-800 bg-red-900/20 p-4">
        <h3 className="text-sm font-semibold text-red-500">Error Loading Audit Events</h3>
        <p className="mt-1 text-sm text-neutral-300">{eventsState.error}</p>
      </div>
    );
  }

  const events = eventsState.data ?? [];

  if (events.length === 0) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8 text-center">
        <Clock className="mx-auto h-12 w-12 text-neutral-600" />
        <p className="mt-3 text-sm text-neutral-400">No audit events found</p>
        <p className="mt-1 text-xs text-neutral-500">
          Audit events are automatically created by the backend for site operations
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Audit Timeline</h2>
          <p className="text-sm text-neutral-400">
            {events.length} event{events.length !== 1 ? "s" : ""} found
          </p>
        </div>
        <button
          onClick={loadAuditEvents}
          className="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-200 transition-colors hover:bg-neutral-700"
        >
          Refresh
        </button>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[11px] top-0 h-full w-px bg-neutral-800" />

        {/* Events */}
        <div className="flex flex-col gap-4">
          {events.map((event) => (
            <AuditEventCard key={event.id} event={event} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Audit Event Card Component
// ============================================================================

interface AuditEventCardProps {
  event: AuditEvent;
}

function AuditEventCard({ event }: AuditEventCardProps) {
  const { icon: Icon, color } = getSeverityConfig(event.severity);

  return (
    <div className="relative flex gap-4">
      {/* Icon */}
      <div className={`relative z-10 flex h-6 w-6 items-center justify-center rounded-full ${color.bg}`}>
        <Icon className={`h-3 w-3 ${color.text}`} />
      </div>

      {/* Content */}
      <div className="flex-1 rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">{event.event_type}</h3>
              <SeverityBadge severity={event.severity} />
            </div>
            <p className="mt-1 text-sm text-neutral-300">{event.description}</p>
            <div className="mt-2 flex items-center gap-4 text-xs text-neutral-400">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatTimestamp(event.timestamp)}
              </div>
              <div>
                Source: <span className="font-mono">{event.source}</span>
              </div>
            </div>
            {event.metadata && Object.keys(event.metadata).length > 0 && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-neutral-500 hover:text-neutral-400">
                  View metadata
                </summary>
                <pre className="mt-2 overflow-auto rounded-lg bg-neutral-950 p-2 text-xs text-neutral-300">
                  {JSON.stringify(event.metadata, null, 2)}
                </pre>
              </details>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Severity Badge Component
// ============================================================================

interface SeverityBadgeProps {
  severity: "INFO" | "WARNING" | "ERROR" | "CRITICAL";
}

function SeverityBadge({ severity }: SeverityBadgeProps) {
  const config = getSeverityConfig(severity);

  return (
    <span className={`rounded-full px-2 py-1 text-[10px] uppercase ${config.badge}`}>
      {severity}
    </span>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function getSeverityConfig(severity: string) {
  switch (severity) {
    case "INFO":
      return {
        icon: Info,
        color: { bg: "bg-blue-900/60", text: "text-blue-300" },
        badge: "bg-blue-900/60 text-blue-300",
      };
    case "WARNING":
      return {
        icon: AlertTriangle,
        color: { bg: "bg-amber-900/60", text: "text-amber-300" },
        badge: "bg-amber-900/60 text-amber-300",
      };
    case "ERROR":
      return {
        icon: XCircle,
        color: { bg: "bg-orange-900/60", text: "text-orange-300" },
        badge: "bg-orange-900/60 text-orange-300",
      };
    case "CRITICAL":
      return {
        icon: AlertCircle,
        color: { bg: "bg-rose-900/60", text: "text-rose-300" },
        badge: "bg-rose-900/60 text-rose-300",
      };
    default:
      return {
        icon: Info,
        color: { bg: "bg-slate-800", text: "text-slate-300" },
        badge: "bg-slate-800 text-slate-300",
      };
  }
}

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
