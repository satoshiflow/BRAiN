"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useState, useEffect } from "react";
import {
  fetchTraceChain,
  fetchAuditEvents,
  type TraceChain,
  type AuditEvent,
  formatErrorMessage,
} from "@/lib/neurorailApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

type SearchForm = {
  entityType: "mission" | "plan" | "job" | "attempt";
  entityId: string;
};

export default function TraceExplorerPage() {
  const [searchForm, setSearchForm] = useState<SearchForm>({
    entityType: "mission",
    entityId: "",
  });

  const [traceState, setTraceState] = useState<LoadState<TraceChain>>({
    loading: false,
  });

  const [auditState, setAuditState] = useState<LoadState<AuditEvent[]>>({
    loading: false,
  });

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchForm.entityId.trim()) return;

    // Load trace chain
    setTraceState({ loading: true });
    setAuditState({ loading: true });

    try {
      const trace = await fetchTraceChain(
        searchForm.entityType,
        searchForm.entityId.trim()
      );
      setTraceState({ data: trace, loading: false });

      // Load audit events for the mission
      if (trace.mission) {
        try {
          const auditResponse = await fetchAuditEvents({
            mission_id: trace.mission.mission_id,
            limit: 100,
          });
          setAuditState({
            data: auditResponse.events,
            loading: false,
          });
        } catch (auditErr) {
          setAuditState({
            loading: false,
            error: formatErrorMessage(auditErr),
          });
        }
      } else {
        setAuditState({ data: [], loading: false });
      }
    } catch (err) {
      setTraceState({
        loading: false,
        error: formatErrorMessage(err),
      });
      setAuditState({ loading: false });
    }
  }

  function renderTraceChain() {
    if (!traceState.data) return null;

    const { mission, plan, job, attempt, resources } = traceState.data;

    return (
      <div className="space-y-3">
        {/* Mission */}
        {mission && (
          <div className="rounded border border-blue-800 bg-blue-950/30 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-mono text-sm font-semibold text-blue-400">
                MISSION
              </h3>
              <span className="font-mono text-xs text-gray-400">
                {mission.created_at}
              </span>
            </div>
            <div className="font-mono text-sm text-gray-300">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">ID:</span>
                <code className="rounded bg-gray-800 px-2 py-0.5 text-yellow-400">
                  {mission.mission_id}
                </code>
              </div>
              {mission.parent_mission_id && (
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className="text-gray-500">Parent:</span>
                  <code className="rounded bg-gray-800 px-1.5 py-0.5 text-gray-400">
                    {mission.parent_mission_id}
                  </code>
                </div>
              )}
              {Object.keys(mission.tags).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(mission.tags).map(([key, value]) => (
                    <span
                      key={key}
                      className="rounded-full bg-blue-900/50 px-2 py-0.5 text-xs text-blue-300"
                    >
                      {key}: {value}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Plan */}
        {plan && (
          <div className="ml-6 rounded border border-purple-800 bg-purple-950/30 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-mono text-sm font-semibold text-purple-400">
                PLAN
              </h3>
              <span className="font-mono text-xs text-gray-400">
                {plan.created_at}
              </span>
            </div>
            <div className="font-mono text-sm text-gray-300">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">ID:</span>
                <code className="rounded bg-gray-800 px-2 py-0.5 text-yellow-400">
                  {plan.plan_id}
                </code>
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs">
                <span className="text-gray-500">Type:</span>
                <span className="text-gray-300">{plan.plan_type}</span>
              </div>
            </div>
          </div>
        )}

        {/* Job */}
        {job && (
          <div className="ml-12 rounded border border-green-800 bg-green-950/30 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-mono text-sm font-semibold text-green-400">
                JOB
              </h3>
              <span className="font-mono text-xs text-gray-400">
                {job.created_at}
              </span>
            </div>
            <div className="font-mono text-sm text-gray-300">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">ID:</span>
                <code className="rounded bg-gray-800 px-2 py-0.5 text-yellow-400">
                  {job.job_id}
                </code>
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs">
                <span className="text-gray-500">Type:</span>
                <span className="text-gray-300">{job.job_type}</span>
              </div>
            </div>
          </div>
        )}

        {/* Attempt */}
        {attempt && (
          <div className="ml-18 rounded border border-amber-800 bg-amber-950/30 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-mono text-sm font-semibold text-amber-400">
                ATTEMPT
              </h3>
              <span className="font-mono text-xs text-gray-400">
                {attempt.created_at}
              </span>
            </div>
            <div className="font-mono text-sm text-gray-300">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">ID:</span>
                <code className="rounded bg-gray-800 px-2 py-0.5 text-yellow-400">
                  {attempt.attempt_id}
                </code>
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs">
                <span className="text-gray-500">Attempt #:</span>
                <span className="text-gray-300">{attempt.attempt_number}</span>
              </div>
              {attempt.retry_reason && (
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className="text-gray-500">Retry Reason:</span>
                  <span className="text-red-400">{attempt.retry_reason}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Resources */}
        {resources.length > 0 && (
          <div className="ml-24 space-y-2">
            {resources.map((resource) => (
              <div
                key={resource.resource_uuid}
                className="rounded border border-gray-700 bg-gray-900/50 p-3"
              >
                <div className="mb-1 flex items-center justify-between">
                  <h3 className="font-mono text-xs font-semibold text-gray-400">
                    RESOURCE
                  </h3>
                  <span className="font-mono text-xs text-gray-500">
                    {resource.created_at}
                  </span>
                </div>
                <div className="font-mono text-xs text-gray-400">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">UUID:</span>
                    <code className="rounded bg-gray-800 px-1.5 py-0.5 text-gray-300">
                      {resource.resource_uuid}
                    </code>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="text-gray-600">Type:</span>
                    <span className="text-gray-400">{resource.resource_type}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderAuditEvents() {
    if (!auditState.data || auditState.data.length === 0) {
      return (
        <p className="text-sm text-gray-500">
          No audit events found for this mission.
        </p>
      );
    }

    return (
      <div className="space-y-2">
        {auditState.data.map((event) => (
          <div
            key={event.audit_id}
            className="rounded border border-gray-700 bg-gray-900/30 p-3"
          >
            <div className="mb-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    event.severity === "error" || event.severity === "critical"
                      ? "bg-red-900/50 text-red-300"
                      : event.severity === "warning"
                        ? "bg-yellow-900/50 text-yellow-300"
                        : "bg-blue-900/50 text-blue-300"
                  }`}
                >
                  {event.severity.toUpperCase()}
                </span>
                <span className="font-mono text-xs text-gray-400">
                  {event.event_type}
                </span>
              </div>
              <span className="font-mono text-xs text-gray-500">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-300">{event.message}</p>
            {event.details && Object.keys(event.details).length > 0 && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-400">
                  Details
                </summary>
                <pre className="mt-1 overflow-x-auto rounded bg-gray-800 p-2 text-xs text-gray-400">
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6 text-gray-100">
      {/* Header */}
      <div className="mb-6">
        <h1 className="mb-2 text-3xl font-bold text-blue-400">
          NeuroRail Trace Explorer
        </h1>
        <p className="text-sm text-gray-400">
          Search and visualize complete execution trace chains
          (mission → plan → job → attempt → resource)
        </p>
      </div>

      {/* Search Form */}
      <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
        <form onSubmit={handleSearch} className="flex flex-col gap-4 sm:flex-row">
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-gray-400">
              Entity Type
            </label>
            <select
              value={searchForm.entityType}
              onChange={(e) =>
                setSearchForm({
                  ...searchForm,
                  entityType: e.target.value as any,
                })
              }
              className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
            >
              <option value="mission">Mission</option>
              <option value="plan">Plan</option>
              <option value="job">Job</option>
              <option value="attempt">Attempt</option>
            </select>
          </div>

          <div className="flex-[2]">
            <label className="mb-1 block text-xs font-medium text-gray-400">
              Entity ID
            </label>
            <input
              type="text"
              value={searchForm.entityId}
              onChange={(e) =>
                setSearchForm({ ...searchForm, entityId: e.target.value })
              }
              placeholder="e.g., m_abc123def456"
              className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={traceState.loading || !searchForm.entityId.trim()}
              className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {traceState.loading ? "Searching..." : "Search"}
            </button>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {traceState.error && (
        <div className="mb-6 rounded border border-red-800 bg-red-950/30 p-4">
          <p className="text-sm font-medium text-red-400">
            ❌ Error: {traceState.error}
          </p>
        </div>
      )}

      {/* Results */}
      {traceState.data && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Trace Chain */}
          <div>
            <h2 className="mb-4 text-xl font-bold text-blue-400">
              Trace Chain
            </h2>
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
              {renderTraceChain()}
            </div>
          </div>

          {/* Audit Events */}
          <div>
            <h2 className="mb-4 text-xl font-bold text-blue-400">
              Audit Events
              {auditState.data && (
                <span className="ml-2 text-sm font-normal text-gray-400">
                  ({auditState.data.length} events)
                </span>
              )}
            </h2>
            <div className="max-h-[700px] overflow-y-auto rounded-lg border border-gray-800 bg-gray-900 p-4">
              {auditState.loading && (
                <p className="text-sm text-gray-500">Loading audit events...</p>
              )}
              {auditState.error && (
                <p className="text-sm text-red-400">
                  Error loading audit events: {auditState.error}
                </p>
              )}
              {!auditState.loading && !auditState.error && renderAuditEvents()}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!traceState.data && !traceState.loading && !traceState.error && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-12 text-center">
          <p className="text-gray-400">
            Enter a Mission, Plan, Job, or Attempt ID above to explore the trace
            chain.
          </p>
        </div>
      )}
    </div>
  );
}
