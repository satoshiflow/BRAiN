"use client";

import React, { useEffect, useState } from "react";
import {
  fetchLearningInfo,
  fetchDemonstrations,
  fetchPolicies,
  startRecording,
  stopRecording,
  learnPolicy,
  type LearningInfo,
  type Demonstration,
  type LearnedPolicy,
  type DemonstrationMode,
  type PolicyLearningRequest,
} from "@/lib/learningApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function LearningPage() {
  const [info, setInfo] = useState<LoadState<LearningInfo>>({ loading: true });
  const [demonstrations, setDemonstrations] = useState<LoadState<Demonstration[]>>({ loading: true });
  const [policies, setPolicies] = useState<LoadState<LearnedPolicy[]>>({ loading: true });
  const [isRecording, setIsRecording] = useState(false);
  const [currentDemoId, setCurrentDemoId] = useState<string | null>(null);

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchLearningInfo()
      .then((d) => setInfo({ data: d, loading: false }))
      .catch((e) => setInfo({ loading: false, error: String(e) }));

    fetchDemonstrations()
      .then((d) => setDemonstrations({ data: d, loading: false }))
      .catch((e) => setDemonstrations({ loading: false, error: String(e) }));

    fetchPolicies()
      .then((d) => setPolicies({ data: d, loading: false }))
      .catch((e) => setPolicies({ loading: false, error: String(e) }));
  }, [refreshKey]);

  const handleStartRecording = async () => {
    const demoId = `demo_${Date.now()}`;
    try {
      await startRecording(demoId, "robot_01", "example_task", "teleoperation");
      setCurrentDemoId(demoId);
      setIsRecording(true);
    } catch (error) {
      console.error("Failed to start recording:", error);
    }
  };

  const handleStopRecording = async () => {
    if (!currentDemoId) return;

    try {
      await stopRecording(currentDemoId, "teleoperation", true);
      setIsRecording(false);
      setCurrentDemoId(null);
      setRefreshKey((k) => k + 1); // Refresh data
    } catch (error) {
      console.error("Failed to stop recording:", error);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">Learning from Demonstration</h1>
        <p className="text-sm text-neutral-400">
          Record human demonstrations, learn policies, and enable robots to replicate complex behaviors.
        </p>
      </header>

      {/* Summary Cards */}
      {info.data && (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <SummaryCard
            title="Total Demonstrations"
            value={info.data.statistics.total_demonstrations}
            subtitle="recorded demos"
            color="sky"
          />
          <SummaryCard
            title="Learned Policies"
            value={info.data.statistics.total_policies}
            subtitle="trained policies"
            color="emerald"
          />
          <SummaryCard
            title="Active Recordings"
            value={info.data.statistics.active_recordings}
            subtitle={isRecording ? "recording now" : "idle"}
            color={isRecording ? "amber" : "purple"}
          />
        </section>
      )}

      {/* Recording Controls */}
      <section>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Recording Controls</h2>
            {isRecording && (
              <span className="flex items-center gap-2 rounded-full bg-red-900/60 px-3 py-1 text-[10px] text-red-300">
                <span className="h-2 w-2 animate-pulse rounded-full bg-red-400"></span>
                RECORDING
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {!isRecording ? (
              <button
                onClick={handleStartRecording}
                className="rounded-lg border border-emerald-700 bg-emerald-900 px-4 py-2 text-sm font-medium text-emerald-300 hover:border-emerald-500"
              >
                Start Recording
              </button>
            ) : (
              <>
                <button
                  onClick={handleStopRecording}
                  className="rounded-lg border border-red-700 bg-red-900 px-4 py-2 text-sm font-medium text-red-300 hover:border-red-500"
                >
                  Stop Recording
                </button>
                {currentDemoId && (
                  <span className="text-xs text-neutral-400">Demo ID: {currentDemoId}</span>
                )}
              </>
            )}
          </div>

          <p className="mt-3 text-[11px] text-neutral-500">
            {isRecording
              ? "Recording in progress. Trajectory points are being captured in real-time."
              : "Start a new demonstration recording. Use teleoperation, kinesthetic teaching, or vision-based methods."}
          </p>
        </div>
      </section>

      {/* Main Content Grid */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Demonstrations */}
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Demonstrations</h2>
            <span className="text-[10px] text-neutral-500">
              {demonstrations.data?.length ?? 0} recorded
            </span>
          </div>

          {demonstrations.loading && (
            <div className="text-xs text-neutral-400">Loading demonstrations...</div>
          )}

          {demonstrations.error && (
            <div className="text-xs text-red-400">{demonstrations.error}</div>
          )}

          {!demonstrations.loading && demonstrations.data && demonstrations.data.length === 0 && (
            <div className="text-xs text-neutral-500">No demonstrations yet. Start recording to create one.</div>
          )}

          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {demonstrations.data?.map((demo) => (
              <DemonstrationCard key={demo.demo_id} demo={demo} />
            ))}
          </div>
        </div>

        {/* Learned Policies */}
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-300">Learned Policies</h2>
            <span className="text-[10px] text-neutral-500">
              {policies.data?.length ?? 0} policies
            </span>
          </div>

          {policies.loading && (
            <div className="text-xs text-neutral-400">Loading policies...</div>
          )}

          {policies.error && (
            <div className="text-xs text-red-400">{policies.error}</div>
          )}

          {!policies.loading && policies.data && policies.data.length === 0 && (
            <div className="text-xs text-neutral-500">No policies learned yet. Train a policy from demonstrations.</div>
          )}

          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {policies.data?.map((policy) => (
              <PolicyCard key={policy.policy_id} policy={policy} />
            ))}
          </div>
        </div>
      </section>

      {/* Learning Algorithms */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-neutral-300">Supported Learning Algorithms</h2>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="flex flex-wrap gap-2">
            {(["behavioral_cloning", "dagger", "gail", "irl"] as const).map((algo) => (
              <span
                key={algo}
                className="rounded-full bg-emerald-900/60 px-3 py-1 text-[10px] font-medium uppercase text-emerald-300"
              >
                {algo}
              </span>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-neutral-500">
            Advanced imitation learning algorithms for policy training from demonstrations.
          </p>
        </div>
      </section>

      {/* Demonstration Modes */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-neutral-300">Demonstration Modes</h2>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="flex flex-wrap gap-2">
            {(["teleoperation", "kinesthetic", "vision_based"] as DemonstrationMode[]).map((mode) => (
              <span
                key={mode}
                className="rounded-full bg-sky-900/60 px-3 py-1 text-[10px] font-medium uppercase text-sky-300"
              >
                {mode}
              </span>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-neutral-500">
            Different methods for capturing human demonstrations: remote control, physical guidance, or visual observation.
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

function DemonstrationCard({ demo }: { demo: Demonstration }) {
  const modeIcons: Record<DemonstrationMode, string> = {
    teleoperation: "🎮",
    kinesthetic: "🤝",
    vision_based: "👁️",
  };

  const successColor = demo.success ? "text-emerald-400" : "text-red-400";
  const statusText = demo.success ? "Success" : "Failed";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-lg">{modeIcons[demo.mode]}</span>
            <span className="text-xs font-semibold text-neutral-200">{demo.task_name}</span>
          </div>
          <span className="text-[10px] text-neutral-500">ID: {demo.demo_id}</span>
          <span className="text-[10px] text-neutral-400">
            Mode: {demo.mode} • Robot: {demo.robot_id}
          </span>
          <span className="text-[10px] text-neutral-400">
            Duration: {demo.duration_s.toFixed(1)}s • Points: {demo.trajectory.length}
          </span>
          <span className={`text-[10px] font-semibold ${successColor}`}>{statusText}</span>
        </div>
      </div>
    </div>
  );
}

function PolicyCard({ policy }: { policy: LearnedPolicy }) {
  const accuracyColor =
    policy.training_accuracy >= 0.9
      ? "text-emerald-400"
      : policy.training_accuracy >= 0.7
        ? "text-amber-400"
        : "text-red-400";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-neutral-200">{policy.task_name}</span>
            <span className="rounded-full bg-emerald-900/60 px-2 py-0.5 text-[9px] font-medium text-emerald-300">
              {policy.algorithm.toUpperCase()}
            </span>
          </div>
          <span className="text-[10px] text-neutral-500">ID: {policy.policy_id}</span>
          <span className="text-[10px] text-neutral-400">
            Trained on {policy.num_demonstrations} demonstrations
          </span>
          <div className="flex items-center gap-3">
            <div className="flex flex-col">
              <span className="text-[9px] text-neutral-500">Training Acc.</span>
              <span className={`text-xs font-bold ${accuracyColor}`}>
                {(policy.training_accuracy * 100).toFixed(1)}%
              </span>
            </div>
            {policy.validation_accuracy !== undefined && (
              <div className="flex flex-col">
                <span className="text-[9px] text-neutral-500">Validation Acc.</span>
                <span className="text-xs font-semibold text-neutral-300">
                  {(policy.validation_accuracy * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
