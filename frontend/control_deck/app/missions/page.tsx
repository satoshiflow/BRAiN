"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  createMission,
  fetchMissions,
  updateMissionStatus,
  type Mission,
  type MissionStatus,
} from "@/lib/missionsApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

type FormState = {
  name: string;
  description: string;
  submitting: boolean;
  error?: string;
};

const STATUS_ORDER: MissionStatus[] = [
  "RUNNING",
  "PENDING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

export default function MissionsOverviewPage() {
  const [missionsState, setMissionsState] = useState<LoadState<Mission[]>>({
    loading: true,
  });
  const [formState, setFormState] = useState<FormState>({
    name: "",
    description: "",
    submitting: false,
  });

  useEffect(() => {
    loadMissions();
  }, []);

  async function loadMissions() {
    setMissionsState((prev) => ({ ...prev, loading: true, error: undefined }));
    try {
      const missions = await fetchMissions();
      missions.sort((a, b) => {
        const ai = STATUS_ORDER.indexOf(a.status);
        const bi = STATUS_ORDER.indexOf(b.status);
        const ascore = ai === -1 ? STATUS_ORDER.length : ai;
        const bscore = bi === -1 ? STATUS_ORDER.length : bi;
        if (ascore !== bscore) return ascore - bscore;
        const at = a.created_at ? new Date(a.created_at).getTime() : 0;
        const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
        return bt - at;
      });
      setMissionsState({ data: missions, loading: false });
    } catch (err) {
      setMissionsState({
        loading: false,
        error: String(err),
      });
    }
  }

  async function handleCreateMission(e: React.FormEvent) {
    e.preventDefault();
    if (!formState.name.trim()) return;
    setFormState((prev) => ({
      ...prev,
      submitting: true,
      error: undefined,
    }));
    try {
      await createMission({
        name: formState.name.trim(),
        description: formState.description.trim() || undefined,
      });
      setFormState({
        name: "",
        description: "",
        submitting: false,
      });
      await loadMissions();
    } catch (err) {
      setFormState((prev) => ({
        ...prev,
        submitting: false,
        error: String(err),
      }));
    }
  }

  async function handleStatusChange(id: string, status: MissionStatus) {
    try {
      await updateMissionStatus(id, status);
      await loadMissions();
    } catch (err) {
      console.error(err);
    }
  }

  const stats = useMemo(() => {
    const list = missionsState.data ?? [];
    const byStatus: Record<string, number> = {};
    for (const m of list) {
      const key = m.status ?? "UNKNOWN";
      byStatus[key] = (byStatus[key] ?? 0) + 1;
    }
    return {
      total: list.length,
      running: byStatus.RUNNING ?? 0,
      pending: byStatus.PENDING ?? 0,
      completed: byStatus.COMPLETED ?? 0,
      failed: byStatus.FAILED ?? 0,
      cancelled: byStatus.CANCELLED ?? 0,
    };
  }, [missionsState.data]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">Missions Overview</h1>
        <p className="text-sm text-neutral-400">
          Überblick über alle aktiven und historischen BRAiN-Missionen.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <DashboardCard label="Total" value={stats.total} />
        <DashboardCard label="Running" value={stats.running} tone="info" />
        <DashboardCard label="Pending" value={stats.pending} />
        <DashboardCard label="Completed" value={stats.completed} tone="success" />
        <DashboardCard label="Failed" value={stats.failed} tone="danger" />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
          <h2 className="text-sm font-semibold text-white">
            Neue Mission anlegen
          </h2>
          <p className="mt-1 text-xs text-neutral-400">
            Name und optional eine kurze Beschreibung eingeben, um eine neue Mission
            zu starten.
          </p>

          <form onSubmit={handleCreateMission} className="mt-4 flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-neutral-300">Name</label>
              <input
                className="h-9 rounded-xl border border-neutral-700 bg-neutral-900 px-3 text-sm text-neutral-100 outline-none focus:border-emerald-500"
                value={formState.name}
                onChange={(e) =>
                  setFormState((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="z.B. Demo Mission"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-neutral-300">Beschreibung</label>
              <textarea
                className="min-h-[80px] rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-emerald-500"
                value={formState.description}
                onChange={(e) =>
                  setFormState((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                placeholder="optional"
              />
            </div>

            {formState.error && (
              <div className="text-xs text-red-400">{formState.error}</div>
            )}

            <button
              type="submit"
              disabled={formState.submitting || !formState.name.trim()}
              className="mt-1 inline-flex h-9 items-center justify-center rounded-full bg-emerald-600 px-4 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {formState.submitting ? "Wird angelegt…" : "Mission anlegen"}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Live Missions</h2>
            {missionsState.loading && (
              <span className="text-xs text-neutral-500">Lade…</span>
            )}
          </div>

          {missionsState.error && (
            <div className="text-xs text-red-400">
              Missionen konnten nicht geladen werden:
              <br />
              {missionsState.error}
            </div>
          )}

          {!missionsState.loading && (missionsState.data ?? []).length === 0 && (
            <div className="text-xs text-neutral-500">
              Noch keine Missionen angelegt.
            </div>
          )}

          <div className="flex flex-col gap-2">
            {(missionsState.data ?? []).map((mission) => (
              <MissionRow
                key={mission.id}
                mission={mission}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function DashboardCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "success" | "danger" | "info";
}) {
  const color =
    tone === "success"
      ? "text-emerald-400"
      : tone === "danger"
        ? "text-red-400"
        : tone === "info"
          ? "text-sky-400"
          : "text-neutral-100";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="text-xs text-neutral-400">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${color}`}>{value}</div>
    </div>
  );
}

function MissionRow({
  mission,
  onStatusChange,
}: {
  mission: Mission;
  onStatusChange: (id: string, status: MissionStatus) => void;
}) {
  const created =
    mission.created_at && !Number.isNaN(Date.parse(mission.created_at))
      ? new Date(mission.created_at)
      : undefined;

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-950/80 px-4 py-3 text-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col">
          <span className="font-medium text-neutral-100">{mission.name}</span>
          {mission.description && (
            <span className="text-xs text-neutral-400">
              {mission.description}
            </span>
          )}
          {created && (
            <span className="mt-1 text-[11px] text-neutral-500">
              Angelegt am {created.toLocaleDateString()}{" "}
              {created.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusBadge status={mission.status} />
          <select
            className="h-7 rounded-full border border-neutral-700 bg-neutral-900 px-2 text-[11px] text-neutral-100 outline-none"
            value={mission.status}
            onChange={(e) =>
              onStatusChange(mission.id, e.target.value as MissionStatus)
            }
          >
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: MissionStatus }) {
  let cls = "bg-neutral-800 text-neutral-200";
  if (status === "RUNNING") cls = "bg-sky-900/60 text-sky-300";
  else if (status === "PENDING") cls = "bg-amber-900/60 text-amber-300";
  else if (status === "COMPLETED") cls = "bg-emerald-900/60 text-emerald-300";
  else if (status === "FAILED") cls = "bg-red-900/60 text-red-300";
  else if (status === "CANCELLED") cls = "bg-neutral-900/80 text-neutral-400";

  return (
    <span
      className={`inline-flex min-w-[88px] justify-center rounded-full px-3 py-1 text-[11px] font-medium ${cls}`}
    >
      {status}
    </span>
  );
}