"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  fetchModuleManifests,
  fetchDNAHistory,
  fetchImmuneHealth,
  type UIModuleManifest,
  type DNAHistoryResponse,
  type AgentDNASnapshot,
  type ImmuneHealthSummary,
} from "@/lib/coreOverviewApi";
import { fetchAgent, type AgentSummary } from "@/lib/agentsApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function CoreAgentDetailPage() {
  const params = useParams();
  const agentId = String(params.agentId ?? "");

  const [agentState, setAgentState] = useState<LoadState<AgentSummary>>({
    loading: true,
  });
  const [modulesState, setModulesState] =
    useState<LoadState<UIModuleManifest[]>>({
      loading: true,
    });
  const [dnaState, setDnaState] = useState<LoadState<DNAHistoryResponse>>({
    loading: true,
  });
  const [immuneState, setImmuneState] =
    useState<LoadState<ImmuneHealthSummary>>({
      loading: true,
    });

  useEffect(() => {
    fetchAgent(agentId)
      .then((agent) => setAgentState({ data: agent, loading: false }))
      .catch((err) =>
        setAgentState({ loading: false, error: String(err) }),
      );
  }, [agentId]);

  useEffect(() => {
    fetchModuleManifests()
      .then((modules) => setModulesState({ data: modules, loading: false }))
      .catch((err) =>
        setModulesState({ loading: false, error: String(err) }),
      );
  }, []);

  useEffect(() => {
    setDnaState((prev) => ({ ...prev, loading: true }));
    fetchDNAHistory(agentId)
      .then((history) => setDnaState({ data: history, loading: false }))
      .catch((err) =>
        setDnaState({ loading: false, error: String(err) }),
      );
  }, [agentId]);

  useEffect(() => {
    setImmuneState((prev) => ({ ...prev, loading: true }));
    fetchImmuneHealth()
      .then((health) => setImmuneState({ data: health, loading: false }))
      .catch((err) =>
        setImmuneState({ loading: false, error: String(err) }),
      );
  }, []);

  const lastSnapshot: AgentDNASnapshot | undefined = useMemo(() => {
    if (!dnaState.data?.snapshots?.length) return undefined;
    const snaps = dnaState.data.snapshots;
    return snaps[snaps.length - 1];
  }, [dnaState.data]);

  const karmaScore = lastSnapshot?.karma_score ?? null;

  const immuneColor =
    immuneState.data?.critical_issues && immuneState.data.critical_issues > 0
      ? "text-red-400"
      : immuneState.data?.active_issues
        ? "text-amber-400"
        : "text-emerald-400";

  const agentLabel =
    agentState.data?.label ??
    (agentId ? `Agent ${agentId}` : "Unbekannter Agent");

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">
          BRAiN Core Agent · {agentLabel}
        </h1>
        <p className="text-sm text-neutral-400">
          Missions · DNA · KARMA · Immune – Überblick für diesen Agenten.
        </p>
        <span className="text-xs text-neutral-500">Agent ID: {agentId}</span>
        {agentState.error && (
          <span className="text-xs text-red-400">
            Agent konnte nicht geladen werden: {agentState.error}
          </span>
        )}
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Modules</h2>
            {modulesState.loading && (
              <span className="text-xs text-neutral-500">Lade…</span>
            )}
          </div>

          {modulesState.error && (
            <div className="text-xs text-red-400">
              Module konnten nicht geladen werden:
              <br />
              {modulesState.error}
            </div>
          )}

          {!modulesState.loading && modulesState.data && (
            <div className="flex flex-col gap-2">
              {modulesState.data.map((mod) => (
                <div
                  key={mod.name}
                  className="rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white">{mod.label}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-neutral-800 text-neutral-300">
                      {mod.category ?? "Core"}
                    </span>
                  </div>
                  {mod.routes?.length ? (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {mod.routes.map((r) => (
                        <span
                          key={r.path}
                          className="text-[11px] rounded-full bg-neutral-800/80 px-2 py-0.5 text-neutral-300"
                        >
                          {r.label}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[11px] text-neutral-500">
                      Keine UI-Routen definiert.
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">DNA & KARMA</h2>
            {dnaState.loading && (
              <span className="text-xs text-neutral-500">Lade…</span>
            )}
          </div>

          {lastSnapshot ? (
            <>
              <div className="text-xs text-neutral-400">
                <div>Agent: {lastSnapshot.agent_id}</div>
                <div>Version: {lastSnapshot.version}</div>
                <div>
                  Zuletzt aktualisiert:{" "}
                    {new Date(lastSnapshot.created_at).toLocaleString()}
                </div>
              </div>

              <div className="mt-2">
                <h3 className="text-xs font-semibold text-neutral-300 mb-1">
                  DNA
                </h3>
                <pre className="text-[11px] rounded-xl bg-black/60 border border-neutral-800 px-3 py-2 text-neutral-200 overflow-x-auto">
                  {JSON.stringify(lastSnapshot.dna, null, 2)}
                </pre>
              </div>

              <div className="mt-2">
                <h3 className="text-xs font-semibold text-neutral-300 mb-1">
                  Traits
                </h3>
                <pre className="text-[11px] rounded-xl bg-black/60 border border-neutral-800 px-3 py-2 text-neutral-200 overflow-x-auto">
                  {JSON.stringify(lastSnapshot.traits, null, 2)}
                </pre>
              </div>

              <div className="mt-2 flex items-center justify-between">
                <span className="text-xs text-neutral-400">KARMA Score</span>
                <span className="text-lg font-semibold text-sky-400">
                  {karmaScore ?? "–"}
                </span>
              </div>
            </>
          ) : dnaState.loading ? null : (
            <div className="text-xs text-neutral-500">
              Keine DNA-Snapshots für diesen Agenten gefunden.
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Immune System</h2>
            {immuneState.loading && (
              <span className="text-xs text-neutral-500">Lade…</span>
            )}
          </div>

          {immuneState.error && (
            <div className="text-xs text-red-400">
              Immune-Status konnte nicht geladen werden:
              <br />
              {immuneState.error}
            </div>
          )}

          {immuneState.data && (
            <>
              <div className="flex items-center justify-between">
                <div className="flex flex-col text-xs text-neutral-400">
                  <span>Active issues: {immuneState.data.active_issues}</span>
                  <span>Critical: {immuneState.data.critical_issues}</span>
                </div>
                <div className={`text-sm font-semibold ${immuneColor}`}>
                  {immuneState.data.critical_issues > 0
                    ? "CRITICAL"
                    : immuneState.data.active_issues > 0
                      ? "WARN"
                      : "HEALTHY"}
                </div>
              </div>

              <div className="mt-3">
                <h3 className="text-xs font-semibold text-neutral-300 mb-1">
                  Last Events
                </h3>
                {immuneState.data.last_events.length === 0 ? (
                  <div className="text-xs text-neutral-500">
                    Keine Events im Zeitraum.
                  </div>
                ) : (
                  <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1">
                    {immuneState.data.last_events.map((ev) => (
                      <div
                        key={ev.id}
                        className="rounded-xl border border-neutral-800 bg-black/60 px-3 py-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-neutral-400">
                            {ev.module ?? "unknown"} · {ev.agent_id ?? "n/a"}
                          </span>
                          <span className="text-[10px] text-neutral-500">
                            {new Date(ev.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-neutral-200">
                          {ev.message}
                        </div>
                        <div className="mt-1 text-[10px] text-neutral-500">
                          {ev.severity} · {ev.type}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}