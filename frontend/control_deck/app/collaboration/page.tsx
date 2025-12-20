"use client";

import React, { useEffect, useState } from "react";
import {
  fetchCollaborationInfo,
  fetchFormations,
  fetchTasks,
  fetchWorldModels,
  createFormation,
  createTask,
  type CollaborationInfo,
  type FormationConfig,
  type CollaborativeTask,
  type SharedWorldModel,
  type FormationType,
  type TaskAllocationStrategy,
} from "@/lib/collaborationApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function CollaborationPage() {
  const [info, setInfo] = useState<LoadState<CollaborationInfo>>({ loading: true });
  const [formations, setFormations] = useState<LoadState<FormationConfig[]>>({ loading: true });
  const [tasks, setTasks] = useState<LoadState<CollaborativeTask[]>>({ loading: true });
  const [worldModels, setWorldModels] = useState<LoadState<SharedWorldModel[]>>({ loading: true });

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchCollaborationInfo()
      .then((d) => setInfo({ data: d, loading: false }))
      .catch((e) => setInfo({ loading: false, error: String(e) }));

    fetchFormations()
      .then((d) => setFormations({ data: d, loading: false }))
      .catch((e) => setFormations({ loading: false, error: String(e) }));

    fetchTasks()
      .then((d) => setTasks({ data: d, loading: false }))
      .catch((e) => setTasks({ loading: false, error: String(e) }));

    fetchWorldModels()
      .then((d) => setWorldModels({ data: d, loading: false }))
      .catch((e) => setWorldModels({ loading: false, error: String(e) }));
  }, [refreshKey]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">Multi-Robot Collaboration</h1>
        <p className="text-sm text-neutral-400">
          Formation control, task allocation, and shared world models for coordinated multi-robot operations.
        </p>
      </header>

      {/* Summary Cards */}
      {info.data && (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <SummaryCard
            title="Active Formations"
            value={info.data.statistics.active_formations}
            subtitle="robot formations"
            color="sky"
          />
          <SummaryCard
            title="Pending Tasks"
            value={info.data.statistics.pending_tasks}
            subtitle="awaiting allocation"
            color="amber"
          />
          <SummaryCard
            title="Allocated Tasks"
            value={info.data.statistics.allocated_tasks}
            subtitle="robots assigned"
            color="emerald"
          />
          <SummaryCard
            title="World Models"
            value={info.data.statistics.world_models}
            subtitle="shared maps"
            color="purple"
          />
        </section>
      )}

      {/* Formations */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-300">Active Formations</h2>
          <span className="text-[10px] text-neutral-500">
            {formations.data?.length ?? 0} formations
          </span>
        </div>

        {formations.loading && (
          <div className="text-xs text-neutral-400">Loading formations...</div>
        )}

        {formations.error && (
          <div className="text-xs text-red-400">{formations.error}</div>
        )}

        {!formations.loading && formations.data && formations.data.length === 0 && (
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4 text-center">
            <div className="text-xs text-neutral-500">No active formations. Create one to get started.</div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {formations.data?.map((formation) => (
            <FormationCard key={formation.formation_id} formation={formation} />
          ))}
        </div>
      </section>

      {/* Collaborative Tasks */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Collaborative Tasks</h2>
            <span className="text-[10px] text-neutral-500">
              {tasks.data?.length ?? 0} tasks
            </span>
          </div>

          {tasks.loading && (
            <div className="text-xs text-neutral-400">Loading tasks...</div>
          )}

          {tasks.error && (
            <div className="text-xs text-red-400">{tasks.error}</div>
          )}

          {!tasks.loading && tasks.data && tasks.data.length === 0 && (
            <div className="text-xs text-neutral-500">No collaborative tasks yet.</div>
          )}

          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {tasks.data?.map((task) => (
              <TaskCard key={task.task_id} task={task} />
            ))}
          </div>
        </div>

        {/* Shared World Models */}
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Shared World Models</h2>
            <span className="text-[10px] text-neutral-500">
              {worldModels.data?.length ?? 0} models
            </span>
          </div>

          {worldModels.loading && (
            <div className="text-xs text-neutral-400">Loading world models...</div>
          )}

          {worldModels.error && (
            <div className="text-xs text-red-400">{worldModels.error}</div>
          )}

          {!worldModels.loading && worldModels.data && worldModels.data.length === 0 && (
            <div className="text-xs text-neutral-500">No shared world models yet.</div>
          )}

          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {worldModels.data?.map((model) => (
              <WorldModelCard key={model.model_id} model={model} />
            ))}
          </div>
        </div>
      </section>

      {/* Formation Types */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-neutral-300">Supported Formation Types</h2>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="flex flex-wrap gap-2">
            {(["line", "column", "wedge", "circle", "grid", "custom"] as FormationType[]).map((type) => (
              <span
                key={type}
                className="rounded-full bg-sky-900/60 px-3 py-1 text-[10px] font-medium uppercase text-sky-300"
              >
                {type}
              </span>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-neutral-500">
            Create formations for coordinated multi-robot navigation and task execution.
          </p>
        </div>
      </section>

      {/* Allocation Strategies */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-neutral-300">Task Allocation Strategies</h2>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="flex flex-wrap gap-2">
            {(["greedy", "auction", "consensus", "learning_based"] as TaskAllocationStrategy[]).map((strategy) => (
              <span
                key={strategy}
                className="rounded-full bg-emerald-900/60 px-3 py-1 text-[10px] font-medium uppercase text-emerald-300"
              >
                {strategy}
              </span>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-neutral-500">
            Intelligent task allocation mechanisms for optimal robot-task matching.
          </p>
        </div>
      </section>

      {/* Module Info */}
      {info.data && (
        <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
          <div className="text-xs text-neutral-400">
            <span className="font-semibold text-neutral-300">{info.data.module}</span> v{info.data.version} •{" "}
            {info.data.description}
          </div>
        </section>
      )}
    </div>
  );
}

// ========== Components ==========

type SummaryCardProps = {
  title: string;
  value: number;
  subtitle: string;
  color: "emerald" | "amber" | "sky" | "purple";
};

function SummaryCard({ title, value, subtitle, color }: SummaryCardProps) {
  const colorClasses = {
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    sky: "text-sky-400",
    purple: "text-purple-400",
  };

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="flex flex-col gap-1">
        <span className="text-xs font-semibold text-neutral-300">{title}</span>
        <span className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</span>
        <span className="text-[11px] text-neutral-500">{subtitle}</span>
      </div>
    </div>
  );
}

function FormationCard({ formation }: { formation: FormationConfig }) {
  const formationIcons: Record<FormationType, string> = {
    line: "━",
    column: "┃",
    wedge: "▼",
    circle: "○",
    grid: "⊞",
    custom: "✦",
  };

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-950/80 px-3 py-3">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-lg">{formationIcons[formation.formation_type]}</span>
            <span className="text-xs font-semibold text-neutral-200">
              {formation.formation_type.toUpperCase()}
            </span>
          </div>
          <span className="text-[10px] text-neutral-500">ID: {formation.formation_id}</span>
        </div>
      </div>
      <div className="mt-2 flex flex-col gap-1">
        <div className="text-[10px] text-neutral-400">
          Leader: <span className="text-sky-400">{formation.leader_id}</span>
        </div>
        <div className="text-[10px] text-neutral-400">
          Robots: <span className="text-neutral-200">{formation.robot_ids.length}</span> •{" "}
          Distance: <span className="text-neutral-200">{formation.inter_robot_distance}m</span>
        </div>
        <div className="text-[10px] text-neutral-400">
          Behavior: <span className="text-emerald-400">{formation.behavior}</span>
        </div>
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: CollaborativeTask }) {
  const statusColors = {
    pending: "bg-amber-900/60 text-amber-300",
    allocated: "bg-sky-900/60 text-sky-300",
    executing: "bg-emerald-900/60 text-emerald-300",
    completed: "bg-neutral-800 text-neutral-400",
    failed: "bg-red-900/60 text-red-300",
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-[9px] font-medium uppercase ${statusColors[task.status]}`}
            >
              {task.status}
            </span>
            <span className="text-[10px] font-semibold text-neutral-300">Priority {task.priority}</span>
          </div>
          <span className="text-xs text-neutral-200">{task.description}</span>
          <span className="text-[10px] text-neutral-500">
            Type: {task.task_type} • Strategy: {task.allocation_strategy}
          </span>
          <span className="text-[10px] text-neutral-400">
            Required: {task.required_robots} • Assigned: {task.assigned_robots.length}
          </span>
          {task.assigned_robots.length > 0 && (
            <div className="text-[10px] text-sky-400">
              Robots: {task.assigned_robots.join(", ")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WorldModelCard({ model }: { model: SharedWorldModel }) {
  const consensusPercent = (model.consensus_level * 100).toFixed(0);
  const consensusColor =
    model.consensus_level >= 0.8
      ? "text-emerald-400"
      : model.consensus_level >= 0.6
        ? "text-amber-400"
        : "text-red-400";

  const lastUpdated = new Date(model.last_updated * 1000);
  const now = Date.now();
  const ageMs = now - model.last_updated * 1000;
  const ageSeconds = Math.floor(ageMs / 1000);
  const ageDisplay =
    ageSeconds < 60
      ? `${ageSeconds}s ago`
      : ageSeconds < 3600
        ? `${Math.floor(ageSeconds / 60)}m ago`
        : `${Math.floor(ageSeconds / 3600)}h ago`;

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-neutral-200">Model {model.model_id}</span>
          <span className="text-[10px] text-neutral-500">
            {model.robot_ids.length} robots contributing
          </span>
          <div className="mt-1 flex items-center gap-2">
            <span className={`text-xs font-bold ${consensusColor}`}>{consensusPercent}%</span>
            <span className="text-[10px] text-neutral-500">consensus</span>
          </div>
          <span className="text-[10px] text-neutral-500">Updated: {ageDisplay}</span>
        </div>
      </div>
    </div>
  );
}
