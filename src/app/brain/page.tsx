"use client";

import { useEffect, useState } from "react";
import {
  brainApi,
  HealthResponse,
  MissionsInfoResponse,
  ConnectorsListResponse,
  AgentsInfoResponse,
  AxeInfoResponse,
} from "@/lib/brainApi";

type StatusState<T> = {
  loading: boolean;
  error: string | null;
  data: T | null;
};

const initialState = { loading: true, error: null, data: null } as const;

export default function BrainOverviewPage() {
  const [health, setHealth] = useState<StatusState<HealthResponse>>({
    ...initialState,
  });
  const [missions, setMissions] = useState<StatusState<MissionsInfoResponse>>({
    ...initialState,
  });
  const [connectors, setConnectors] =
    useState<StatusState<ConnectorsListResponse>>({ ...initialState });
  const [agents, setAgents] = useState<StatusState<AgentsInfoResponse>>({
    ...initialState,
  });
  const [axeInfo, setAxeInfo] = useState<StatusState<AxeInfoResponse>>({
    ...initialState,
  });

  useEffect(() => {
    const load = async () => {
      try {
        const [h, m, c, a, x] = await Promise.all([
          brainApi.getHealth(),
          brainApi.getMissionsInfo(),
          brainApi.getConnectorsList(),
          brainApi.getAgentsInfo(),
          brainApi.getAxeInfo().catch((err) => {
            // AXE ist optional – Fehler nur lokal anzeigen
            throw { axe: err };
          }),
        ]);

        setHealth({ loading: false, error: null, data: h });
        setMissions({ loading: false, error: null, data: m });
        setConnectors({ loading: false, error: null, data: c });
        setAgents({ loading: false, error: null, data: a });
        setAxeInfo({ loading: false, error: null, data: x });
      } catch (err: any) {
        const axeErr = err?.axe;

        if (axeErr) {
          setAxeInfo({
            loading: false,
            error: axeErr?.message ?? String(axeErr),
            data: null,
          });
        } else {
          const msg = err?.message ?? String(err);
          setHealth({ loading: false, error: msg, data: null });
          setMissions({ loading: false, error: msg, data: null });
          setConnectors({ loading: false, error: msg, data: null });
          setAgents({ loading: false, error: msg, data: null });
          setAxeInfo({ loading: false, error: msg, data: null });
        }
      }
    };

    load();
  }, []);

  const connectorCount = connectors.data?.connectors?.length ?? 0;
  const agentCount = agents.data?.agents?.length ?? 0;

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight">
          BRAiN Control Center
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Überblick über Health, Missions, Connectors, Agents und AXE.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        {/* Backend Health */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Backend
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-50">
            {health.loading
              ? "Checking…"
              : health.error
              ? "Error"
              : health.data?.status ?? "Unknown"}
          </h2>
          {health.data?.uptime !== undefined && !health.loading && !health.error && (
            <p className="mt-1 text-xs text-slate-400">
              Uptime: {Math.round(health.data.uptime)}s
            </p>
          )}
          {health.error && (
            <p className="mt-2 text-xs text-red-400 break-all">{health.error}</p>
          )}
        </div>

        {/* Missions */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Missions
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-50">
            {missions.loading
              ? "Loading…"
              : missions.error
              ? "Error"
              : missions.data?.name ?? "Mission System"}
          </h2>
          {!missions.loading && !missions.error && (
            <p className="mt-1 text-xs text-slate-400">
              Version: {missions.data?.version ?? "n/a"}
            </p>
          )}
          {missions.error && (
            <p className="mt-2 text-xs text-red-400 break-all">
              {missions.error}
            </p>
          )}
        </div>

        {/* Connectors */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Connectors
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-50">
            {connectors.loading
              ? "Loading…"
              : connectors.error
              ? "Error"
              : `${connectorCount} configured`}
          </h2>
          {connectors.error && (
            <p className="mt-2 text-xs text-red-400 break-all">
              {connectors.error}
            </p>
          )}
        </div>

        {/* Agents */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Agents
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-50">
            {agents.loading
              ? "Loading…"
              : agents.error
              ? "Error"
              : `${agentCount} agents`}
          </h2>
          {agents.error && (
            <p className="mt-2 text-xs text-red-400 break-all">
              {agents.error}
            </p>
          )}
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        {/* Agents Detail */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              Agent Übersicht
            </h2>
          </div>
          {agents.loading && (
            <p className="text-xs text-slate-400">Lade Agenten …</p>
          )}
          {agents.error && (
            <p className="text-xs text-red-400">{agents.error}</p>
          )}
          {!agents.loading && !agents.error && agents.data?.agents && (
            <ul className="mt-2 space-y-1 text-xs">
              {agents.data.agents.map((agent) => (
                <li
                  key={String(agent.id)}
                  className="flex items-center justify-between rounded-md bg-slate-950/40 px-2 py-1"
                >
                  <span className="font-medium text-slate-100">
                    {agent.name}
                  </span>
                  <span className="text-[10px] uppercase tracking-wide text-slate-400">
                    {agent.status ?? "unknown"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* AXE Info */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              AXE
            </h2>
          </div>
          {axeInfo.loading && (
            <p className="text-xs text-slate-400">Lade AXE-Info …</p>
          )}
          {axeInfo.error && (
            <p className="text-xs text-red-400 break-all">{axeInfo.error}</p>
          )}
          {!axeInfo.loading && !axeInfo.error && axeInfo.data && (
            <div className="space-y-1 text-xs text-slate-200">
              <p>
                <span className="text-slate-400">Name:</span>{" "}
                {axeInfo.data.name}
              </p>
              <p>
                <span className="text-slate-400">Version:</span>{" "}
                {axeInfo.data.version}
              </p>
              {axeInfo.data.description && (
                <p className="text-slate-300">{axeInfo.data.description}</p>
              )}
            </div>
          )}
          <div className="mt-4">
            <a
              href="/brain/debug"
              className="inline-flex items-center rounded-md border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-800"
            >
              Open AXE Console
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}