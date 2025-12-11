"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  fetchCoreHealth,
  fetchMissionsHealth,
  fetchSupervisorHealth,
  fetchMissionsOverviewStats,
  fetchThreatsOverviewStats,
  fetchImmuneHealth,
  type CoreHealth,
  type MissionsHealth,
  type SupervisorHealth,
  type MissionsOverviewStats,
  type ThreatsOverviewStats,
  type ImmuneHealthSummary,
} from "@/lib/dashboardApi";
import { fetchMissions, type Mission } from "@/lib/missionsApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

type MissionStatus = Mission["status"];

const STATUS_ORDER: MissionStatus[] = [
  "RUNNING",
  "PENDING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

export default function DashboardPage() {
  const [coreHealth, setCoreHealth] = useState<LoadState<CoreHealth>>({
    loading: true,
  });
  const [missionsHealth, setMissionsHealth] =
    useState<LoadState<MissionsHealth>>({
      loading: true,
    });
  const [supervisorHealth, setSupervisorHealth] =
    useState<LoadState<SupervisorHealth>>({
      loading: true,
    });
  const [missionsStats, setMissionsStats] =
    useState<LoadState<MissionsOverviewStats>>({
      loading: true,
    });
  const [threatsStats, setThreatsStats] =
    useState<LoadState<ThreatsOverviewStats>>({
      loading: true,
    });
  const [immuneState, setImmuneState] =
    useState<LoadState<ImmuneHealthSummary>>({
      loading: true,
    });
  const [missionsState, setMissionsState] = useState<LoadState<Mission[]>>({
    loading: true,
  });

  useEffect(() => {
    fetchCoreHealth()
      .then((d) => setCoreHealth({ data: d, loading: false }))
      .catch((e) =>
        setCoreHealth({ loading: false, error: String(e) }),
      );

    fetchMissionsHealth()
      .then((d) => setMissionsHealth({ data: d, loading: false }))
      .catch((e) =>
        setMissionsHealth({ loading: false, error: String(e) }),
      );

    fetchSupervisorHealth()
      .then((d) => setSupervisorHealth({ data: d, loading: false }))
      .catch((e) =>
        setSupervisorHealth({ loading: false, error: String(e) }),
      );

    fetchMissionsOverviewStats()
      .then((d) => setMissionsStats({ data: d, loading: false }))
      .catch((e) =>
        setMissionsStats({ loading: false, error: String(e) }),
      );

    fetchThreatsOverviewStats()
      .then((d) => setThreatsStats({ data: d, loading: false }))
      .catch((e) =>
        setThreatsStats({ loading: false, error: String(e) }),
      );

    fetchImmuneHealth()
      .then((d) => setImmuneState({ data: d, loading: false }))
      .catch((e) =>
        setImmuneState({ loading: false, error: String(e) }),
      );

    fetchMissions()
      .then((list) => {
        const sorted = [...list].sort((a, b) => {
          const ai = STATUS_ORDER.indexOf(a.status);
          const bi = STATUS_ORDER.indexOf(b.status);
          const ascore = ai === -1 ? STATUS_ORDER.length : ai;
          const bscore = bi === -1 ? STATUS_ORDER.length : bi;
          if (ascore !== bscore) return ascore - bscore;
          const at = a.created_at ? new Date(a.created_at).getTime() : 0;
          const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
          return bt - at;
        });
        setMissionsState({ data: sorted, loading: false });
      })
      .catch((e) =>
        setMissionsState({ loading: false, error: String(e) }),
      );
  }, []);

  const coreStatus = coreHealth.data?.status ?? "unknown";
  const missionsRunning = missionsHealth.data?.running ?? 0;
  const missionsPending = missionsHealth.data?.pending ?? 0;
  const missionsCompleted = missionsHealth.data?.completed ?? 0;
  const missionsFailed = missionsHealth.data?.failed ?? 0;

  const supervisorStatus = supervisorHealth.data?.status ?? "unknown";
  const supervisorRunning = supervisorHealth.data?.running ?? 0;
  const supervisorCompleted = supervisorHealth.data?.completed ?? 0;
  const supervisorFailed = supervisorHealth.data?.failed ?? 0;
  const supervisorCancelled = supervisorHealth.data?.cancelled ?? 0;

  const threatsTotal = threatsStats.data?.total ?? 0;
  const threatsCritical = threatsStats.data?.critical ?? 0;

  const immuneCritical = immuneState.data?.critical_issues ?? 0;

  const latestMissions = useMemo(
    () => (missionsState.data ?? []).slice(0, 5),
    [missionsState.data],
  );

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">BRAiN Dashboard</h1>
        <p className="text-sm text-neutral-400">
          Core · Missions · Supervisor · Immune – Überblick über den aktuellen Systemzustand.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <StatusCard
          title="CORE API"
          status={coreStatus}
          primary={coreStatus === "ok" ? "Online" : "Check system"}
          lines={[
            coreHealth.data?.env ? `Env: ${coreHealth.data.env}` : undefined,
            coreHealth.data?.version
              ? `Version: ${coreHealth.data.version}`
              : undefined,
          ].filter(Boolean) as string[]}
          loading={coreHealth.loading}
          error={coreHealth.error}
        />
        <MissionsSummaryCard
          title="MISSIONS"
          total={missionsStats.data?.total ?? 0}
          running={missionsRunning}
          pending={missionsPending}
          completed={missionsCompleted}
          failed={missionsFailed}
          loading={missionsHealth.loading || missionsStats.loading}
          error={missionsHealth.error || missionsStats.error}
        />
        <SupervisorSummaryCard
          title="SUPERVISOR"
          status={supervisorStatus}
          running={supervisorRunning}
          completed={supervisorCompleted}
          failed={supervisorFailed}
          cancelled={supervisorCancelled}
          loading={supervisorHealth.loading}
          error={supervisorHealth.error}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ActivityOverviewCard />
        <ImmuneThreatsCard
          threatsTotal={threatsTotal}
          threatsCritical={threatsCritical}
          activeIssues={immuneState.data?.active_issues ?? 0}
          criticalIssues={immuneCritical}
          loading={immuneState.loading || threatsStats.loading}
          error={immuneState.error || threatsStats.error}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <LatestMissionsCard
          missions={latestMissions}
          loading={missionsState.loading}
          error={missionsState.error}
        />
        <QuickActionsCard />
      </section>
    </div>
  );
}

type StatusCardProps = {
  title: string;
  status: string;
  primary: string;
  lines?: string[];
  loading?: boolean;
  error?: string;
};

function StatusCard({
  title,
  status,
  primary,
  lines = [],
  loading,
  error,
}: StatusCardProps) {
  const color =
    status === "ok"
      ? "bg-emerald-500"
      : status === "degraded"
        ? "bg-amber-400"
        : "bg-red-500";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-neutral-300">
            {title}
          </span>
          {loading ? (
            <span className="text-sm text-neutral-400">
              Loading…
            </span>
          ) : (
            <>
              <span className="text-sm text-neutral-200">{primary}</span>
              {lines.map((line) => (
                <span
                  key={line}
                  className="text-[11px] text-neutral-500"
                >
                  {line}
                </span>
              ))}
            </>
          )}
        </div>
        <span className={`mt-1 h-2 w-2 rounded-full ${color}`} />
      </div>
      {error && (
        <div className="mt-2 text-[11px] text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}

type MissionsSummaryCardProps = {
  title: string;
  total: number;
  running: number;
  pending: number;
  completed: number;
  failed: number;
  loading?: boolean;
  error?: string;
};

function MissionsSummaryCard({
  title,
  total,
  running,
  pending,
  completed,
  failed,
  loading,
  error,
}: MissionsSummaryCardProps) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-neutral-300">
            {title}
          </span>
          {loading ? (
            <span className="mt-1 text-sm text-neutral-400">
              Loading…
            </span>
          ) : (
            <span className="mt-1 text-sm text-neutral-200">
              {total} Missions
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-[11px] text-neutral-400">
        <MiniKpi label="Running" value={running} tone="info" />
        <MiniKpi label="Pending" value={pending} tone="warn" />
        <MiniKpi label="Done" value={completed} tone="success" />
        <MiniKpi label="Failed" value={failed} tone="danger" />
      </div>
      {error && (
        <div className="mt-2 text-[11px] text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}

type SupervisorSummaryCardProps = {
  title: string;
  status: string;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  loading?: boolean;
  error?: string;
};

function SupervisorSummaryCard({
  title,
  status,
  running,
  completed,
  failed,
  cancelled,
  loading,
  error,
}: SupervisorSummaryCardProps) {
  const color =
    status === "ok"
      ? "bg-emerald-500"
      : status === "degraded"
        ? "bg-amber-400"
        : "bg-red-500";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-neutral-300">
            {title}
          </span>
          {loading ? (
            <span className="mt-1 text-sm text-neutral-400">
              Loading…
            </span>
          ) : (
            <span className="mt-1 text-sm text-neutral-200">
              Status: {status || "unknown"}
            </span>
          )}
        </div>
        <span className={`mt-1 h-2 w-2 rounded-full ${color}`} />
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-[11px] text-neutral-400">
        <MiniKpi label="Running" value={running} tone="info" />
        <MiniKpi label="Done" value={completed} tone="success" />
        <MiniKpi label="Failed" value={failed} tone="danger" />
        <MiniKpi label="Cancelled" value={cancelled} />
      </div>
      {error && (
        <div className="mt-2 text-[11px] text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}

type MiniKpiProps = {
  label: string;
  value: number;
  tone?: "success" | "danger" | "info" | "warn";
};

function MiniKpi({ label, value, tone }: MiniKpiProps) {
  const color =
    tone === "success"
      ? "text-emerald-400"
      : tone === "danger"
        ? "text-red-400"
        : tone === "info"
          ? "text-sky-400"
          : tone === "warn"
            ? "text-amber-400"
            : "text-neutral-200";

  return (
    <div className="flex flex-col">
      <span className="text-neutral-500">{label}</span>
      <span className={color}>{value}</span>
    </div>
  );
}

function ActivityOverviewCard() {
  return (
    <div className="lg:col-span-2 rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-neutral-300">
            Activity overview
          </span>
          <span className="text-[11px] text-neutral-500">
            Quick overview of recent system activity.
          </span>
        </div>
        <span className="rounded-full border border-neutral-700 px-2 py-1 text-[10px] text-neutral-400">
          Demo
        </span>
      </div>
      <div className="mt-4 flex h-40 items-center justify-center rounded-xl border border-dashed border-neutral-700/70 text-xs text-neutral-500">
        Chart placeholder – später echte Telemetrie.
      </div>
    </div>
  );
}

type ImmuneThreatsCardProps = {
  threatsTotal: number;
  threatsCritical: number;
  activeIssues: number;
  criticalIssues: number;
  loading?: boolean;
  error?: string;
};

function ImmuneThreatsCard({
  threatsTotal,
  threatsCritical,
  activeIssues,
  criticalIssues,
  loading,
  error,
}: ImmuneThreatsCardProps) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-neutral-300">
            Immune & Threats
          </span>
          <span className="text-[11px] text-neutral-500">
            Aktive Sicherheitslage des Systems.
          </span>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 text-xs text-neutral-400">Loading…</div>
      ) : (
        <div className="mt-2 grid grid-cols-2 gap-3 text-[11px] text-neutral-400">
          <MiniKpi label="Threats total" value={threatsTotal} />
          <MiniKpi
            label="Critical threats"
            value={threatsCritical}
            tone="danger"
          />
          <MiniKpi
            label="Active issues"
            value={activeIssues}
            tone="warn"
          />
          <MiniKpi
            label="Critical issues"
            value={criticalIssues}
            tone="danger"
          />
        </div>
      )}

      {error && (
        <div className="mt-2 text-[11px] text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}

type LatestMissionsCardProps = {
  missions: Mission[];
  loading?: boolean;
  error?: string;
};

function LatestMissionsCard({
  missions,
  loading,
  error,
}: LatestMissionsCardProps) {
  return (
    <div className="lg:col-span-2 rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-neutral-300">
            Live Missions
          </span>
          <span className="text-[11px] text-neutral-500">
            Letzte Aktivitäten aus dem Missionssystem.
          </span>
        </div>
      </div>

      {loading && (
        <div className="mt-2 text-xs text-neutral-400">
          Loading missions…
        </div>
      )}

      {error && (
        <div className="mt-2 text-[11px] text-red-400">
          {error}
        </div>
      )}

      {!loading && missions.length === 0 && !error && (
        <div className="mt-2 text-xs text-neutral-500">
          Noch keine Missionen angelegt.
        </div>
      )}

      <div className="mt-3 flex flex-col gap-2">
        {missions.map((m) => (
          <div
            key={m.id}
            className="rounded-2xl border border-neutral-800 bg-neutral-950/80 px-3 py-2 text-xs"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex flex-col">
                <span className="text-neutral-100">{m.name}</span>
                {m.description && (
                  <span className="text-[11px] text-neutral-400">
                    {m.description}
                  </span>
                )}
                {m.created_at && (
                  <span className="mt-1 text-[10px] text-neutral-500">
                    {new Date(m.created_at).toLocaleString()}
                  </span>
                )}
              </div>
              <StatusBadge status={m.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: MissionStatus }) {
  let cls = "bg-neutral-800 text-neutral-200";
  if (status === "RUNNING") cls = "bg-sky-900/60 text-sky-300";
  else if (status === "PENDING") cls = "bg-amber-900/60 text-amber-300";
  else if (status === "COMPLETED")
    cls = "bg-emerald-900/60 text-emerald-300";
  else if (status === "FAILED") cls = "bg-red-900/60 text-red-300";
  else if (status === "CANCELLED")
    cls = "bg-neutral-900/80 text-neutral-400";

  return (
    <span
      className={`inline-flex min-w-[88px] justify-center rounded-full px-3 py-1 text-[10px] font-medium ${cls}`}
    >
      {status}
    </span>
  );
}

function QuickActionsCard() {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
      <div className="mb-2 flex flex-col">
        <span className="text-xs font-semibold text-neutral-300">
          Quick Actions
        </span>
        <span className="text-[11px] text-neutral-500">
          Häufige Kontroll-Operationen für den BRAiN Core.
        </span>
      </div>
      <div className="mt-3 flex flex-col gap-2 text-xs">
        <a
          href="/missions"
          className="flex items-center justify-between rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100 hover:border-emerald-500"
        >
          <span>Neue Mission anlegen</span>
          <span className="text-[10px] text-neutral-500">/missions</span>
        </a>
        <a
          href="/core/agents"
          className="flex items-center justify-between rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100 hover:border-emerald-500"
        >
          <span>System Agents überwachen</span>
          <span className="text-[10px] text-neutral-500">/core/agents</span>
        </a>
        <a
          href="/core/modules"
          className="flex items-center justify-between rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100 hover:border-emerald-500"
        >
          <span>Core Modules prüfen</span>
          <span className="text-[10px] text-neutral-500">/core/modules</span>
        </a>
        <a
          href="/immune"
          className="flex items-center justify-between rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100 hover:border-emerald-500"
        >
          <span>Threats & Immune Events</span>
          <span className="text-[10px] text-neutral-500">/immune</span>
        </a>
      </div>
    </div>
  );
}