"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  runtimeControlApi,
  type ResolverResponse,
  type RuntimeActiveOverride,
  type RuntimeControlInfo,
  type RuntimeControlTimelineEvent,
  type RuntimeDecisionContext,
  type RuntimeRegistryVersionItem,
  type RuntimeOverrideRequestItem,
} from "@/lib/api/runtime-control";

const defaultContext: RuntimeDecisionContext = {
  environment: "local",
  mission_type: "general",
  skill_type: "skill.run.execute",
  agent_role: "operator",
  risk_score: 0.2,
  budget_state: { remaining_credits: 2500 },
  system_health: { safe_mode: false },
  feature_context: {
    feature_flags: { runtime_control_ui_preview: true },
    manual_overrides: [],
  },
};

const defaultRequestValue = "\"openclaw\"";

export default function RuntimeControlPage() {
  const [info, setInfo] = useState<RuntimeControlInfo | null>(null);
  const [requests, setRequests] = useState<RuntimeOverrideRequestItem[]>([]);
  const [activeOverrides, setActiveOverrides] = useState<RuntimeActiveOverride[]>([]);
  const [registryVersions, setRegistryVersions] = useState<RuntimeRegistryVersionItem[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<RuntimeControlTimelineEvent[]>([]);
  const [contextJson, setContextJson] = useState(JSON.stringify(defaultContext, null, 2));
  const [result, setResult] = useState<ResolverResponse | null>(null);
  const [requestKey, setRequestKey] = useState("workers.selection.default_executor");
  const [requestValue, setRequestValue] = useState(defaultRequestValue);
  const [requestReason, setRequestReason] = useState("Temporary runtime worker pin for maintenance");
  const [registryPatch, setRegistryPatch] = useState('{"routing":{"llm":{"default_provider":"ollama"}}}');
  const [registryReason, setRegistryReason] = useState("Runtime registry baseline");
  const [isLoading, setIsLoading] = useState(true);
  const [isResolving, setIsResolving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [infoPayload, requestsPayload, activePayload, registryPayload, timelinePayload] = await Promise.all([
        runtimeControlApi.getInfo(),
        runtimeControlApi.listRequests(),
        runtimeControlApi.listActiveOverrides(),
        runtimeControlApi.listRegistryVersions(),
        runtimeControlApi.listTimeline(120),
      ]);
      setInfo(infoPayload);
      setRequests(requestsPayload.items);
      setActiveOverrides(activePayload.items);
      setRegistryVersions(registryPayload.items);
      setTimelineEvents(timelinePayload.items);
      setError(null);
    } catch (err) {
      console.error("Failed to load runtime control data", err);
      setError("Konnte Runtime-Control-Daten nicht laden");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const pendingRequests = useMemo(
    () => requests.filter((item) => item.status === "pending"),
    [requests]
  );

  const resolveDecision = async () => {
    setIsResolving(true);
    try {
      const parsed = JSON.parse(contextJson) as RuntimeDecisionContext;
      const payload = await runtimeControlApi.resolve(parsed);
      setResult(payload);
      setError(null);
    } catch (err) {
      console.error("Failed to resolve runtime decision", err);
      setError("Resolver-Aufruf fehlgeschlagen. Bitte JSON-Kontext pruefen.");
    } finally {
      setIsResolving(false);
    }
  };

  const createRequest = async () => {
    setIsSubmitting(true);
    try {
      const value = JSON.parse(requestValue);
      await runtimeControlApi.createRequest({
        key: requestKey,
        value,
        reason: requestReason,
        tenant_scope: "tenant",
      });
      await loadData();
      setError(null);
    } catch (err) {
      console.error("Failed to create override request", err);
      setError("Override-Request konnte nicht erstellt werden. JSON-Value pruefen.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const approveRequest = async (requestId: string) => {
    try {
      await runtimeControlApi.approveRequest(requestId, "Approved via ControlDeck runtime-control page");
      await loadData();
      setError(null);
    } catch (err) {
      console.error("Failed to approve override request", err);
      setError("Approve fehlgeschlagen (Admin role erforderlich)");
    }
  };

  const rejectRequest = async (requestId: string) => {
    try {
      await runtimeControlApi.rejectRequest(requestId, "Rejected via ControlDeck runtime-control page");
      await loadData();
      setError(null);
    } catch (err) {
      console.error("Failed to reject override request", err);
      setError("Reject fehlgeschlagen (Admin role erforderlich)");
    }
  };

  const createRegistryVersion = async () => {
    try {
      await runtimeControlApi.createRegistryVersion({
        scope: "tenant",
        config_patch: JSON.parse(registryPatch) as Record<string, unknown>,
        reason: registryReason,
      });
      await loadData();
      setError(null);
    } catch (err) {
      console.error("Failed to create registry version", err);
      setError("Registry version konnte nicht erstellt werden (JSON pruefen)");
    }
  };

  const promoteRegistryVersion = async (versionId: string) => {
    try {
      await runtimeControlApi.promoteRegistryVersion(versionId, "Promoted via ControlDeck runtime-control page");
      await loadData();
      setError(null);
    } catch (err) {
      console.error("Failed to promote registry version", err);
      setError("Promotion fehlgeschlagen (Admin role erforderlich)");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Runtime Control Plane</h2>
        <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
          Effective Runtime Decision View fuer Registry - Resolver - Policy - Override - Enforcement - Audit.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {info && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">{info.name}</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">Resolver path: {info.resolver_path}</p>
          <div className="flex flex-wrap gap-2">
            {info.override_priority.map((item) => (
              <span
                key={item}
                className="px-2 py-1 rounded-md text-xs bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Resolver Context</h3>
          <textarea
            value={contextJson}
            onChange={(e) => setContextJson(e.target.value)}
            className="w-full min-h-[320px] font-mono text-xs rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 p-3 text-slate-800 dark:text-slate-100"
          />
          <button
            onClick={resolveDecision}
            disabled={isResolving}
            className="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isResolving ? "Resolving..." : "Resolve Effective Decision"}
          </button>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Create Override Request</h3>
          <input
            value={requestKey}
            onChange={(e) => setRequestKey(e.target.value)}
            className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 p-2 text-sm"
            placeholder="workers.selection.default_executor"
          />
          <textarea
            value={requestValue}
            onChange={(e) => setRequestValue(e.target.value)}
            className="w-full min-h-[80px] font-mono text-xs rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 p-2"
            placeholder='"openclaw"'
          />
          <input
            value={requestReason}
            onChange={(e) => setRequestReason(e.target.value)}
            className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 p-2 text-sm"
            placeholder="Reason"
          />
          <button
            onClick={createRequest}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isSubmitting ? "Submitting..." : "Submit Change Request"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Pending Requests ({pendingRequests.length})</h3>
          {pendingRequests.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Keine pending requests.</p>
          ) : (
            pendingRequests.map((item) => (
              <div key={item.request_id} className="rounded-md border border-slate-200 dark:border-slate-700 p-3 space-y-2">
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{item.request_id}</p>
                <p className="text-sm"><span className="font-medium">{item.key}</span> = <code>{JSON.stringify(item.value)}</code></p>
                <p className="text-xs text-slate-600 dark:text-slate-300">{item.reason}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => approveRequest(item.request_id)}
                    className="px-3 py-1 text-xs rounded-md bg-green-600 text-white hover:bg-green-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => rejectRequest(item.request_id)}
                    className="px-3 py-1 text-xs rounded-md bg-red-600 text-white hover:bg-red-700"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Active Overrides ({activeOverrides.length})</h3>
          {activeOverrides.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Keine aktiven Overrides.</p>
          ) : (
            activeOverrides.map((item) => (
              <div key={item.request_id} className="rounded-md border border-slate-200 dark:border-slate-700 p-3">
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{item.request_id}</p>
                <p className="text-sm"><span className="font-medium">{item.key}</span> = <code>{JSON.stringify(item.value)}</code></p>
                <p className="text-xs text-slate-600 dark:text-slate-300">{item.reason}</p>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Registry Versions ({registryVersions.length})</h3>
          <textarea
            value={registryPatch}
            onChange={(e) => setRegistryPatch(e.target.value)}
            className="w-full min-h-[90px] font-mono text-xs rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 p-2"
          />
          <input
            value={registryReason}
            onChange={(e) => setRegistryReason(e.target.value)}
            className="w-full rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 p-2 text-sm"
            placeholder="Reason"
          />
          <button
            onClick={createRegistryVersion}
            className="px-4 py-2 text-sm rounded-md bg-violet-600 text-white hover:bg-violet-700"
          >
            Create Registry Draft
          </button>
          <div className="space-y-2">
            {registryVersions.map((item) => (
              <div key={item.version_id} className="rounded-md border border-slate-200 dark:border-slate-700 p-3">
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{item.version_id}</p>
                <p className="text-sm">status: <span className="font-medium">{item.status}</span></p>
                <p className="text-xs text-slate-600 dark:text-slate-300">{item.reason}</p>
                <pre className="mt-2 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded p-2 overflow-auto max-h-24">
                  {JSON.stringify(item.config_patch, null, 2)}
                </pre>
                {item.status === "draft" && (
                  <button
                    onClick={() => promoteRegistryVersion(item.version_id)}
                    className="mt-2 px-3 py-1 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                  >
                    Promote
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Audit Timeline ({timelineEvents.length})</h3>
          <div className="space-y-2 max-h-[420px] overflow-auto">
            {timelineEvents.map((item) => (
              <div key={item.event_id} className="rounded-md border border-slate-200 dark:border-slate-700 p-3">
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{item.created_at}</p>
                <p className="text-sm text-slate-800 dark:text-slate-100">{item.event_type}</p>
                <p className="text-xs text-slate-600 dark:text-slate-300">{item.entity_type}:{item.entity_id}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">actor: {item.actor_id ?? "system"}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-4">
        <h3 className="font-medium text-slate-900 dark:text-slate-100">Effective Decision</h3>
        {!result ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Noch keine Entscheidung berechnet.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <p className="text-slate-500 dark:text-slate-400">Decision ID</p>
                <p className="font-mono text-xs mt-1">{result.decision_id}</p>
              </div>
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <p className="text-slate-500 dark:text-slate-400">Validation</p>
                <p className={result.validation.valid ? "text-green-600" : "text-red-600"}>
                  {result.validation.valid ? "valid" : "invalid"}
                </p>
              </div>
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <p className="text-slate-500 dark:text-slate-400">Selected Model</p>
                <p>{result.selected_model}</p>
              </div>
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <p className="text-slate-500 dark:text-slate-400">Selected Worker / Route</p>
                <p>{result.selected_worker} / {result.selected_route}</p>
              </div>
            </div>

            <pre className="text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md p-3 overflow-auto max-h-72">
              {JSON.stringify(
                {
                  applied_policies: result.applied_policies,
                  applied_overrides: result.applied_overrides,
                  explain_trace: result.explain_trace,
                  effective_config: result.effective_config,
                },
                null,
                2
              )}
            </pre>
          </>
        )}
      </div>
    </div>
  );
}
