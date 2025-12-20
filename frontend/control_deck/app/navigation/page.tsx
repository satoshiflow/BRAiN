"use client";

import React, { useEffect, useState } from "react";
import {
  fetchNavigationInfo,
  fetchSocialParams,
  updateSocialParams,
  type NavigationInfo,
  type SocialNavigationParams,
  type NavigationContext,
  type PathPlanningMode,
  type ObstacleAvoidanceStrategy,
} from "@/lib/navigationApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function NavigationPage() {
  const [info, setInfo] = useState<LoadState<NavigationInfo>>({ loading: true });
  const [socialParams, setSocialParams] = useState<LoadState<SocialNavigationParams>>({ loading: true });
  const [editingParams, setEditingParams] = useState(false);
  const [localParams, setLocalParams] = useState<SocialNavigationParams | null>(null);

  useEffect(() => {
    fetchNavigationInfo()
      .then((d) => setInfo({ data: d, loading: false }))
      .catch((e) => setInfo({ loading: false, error: String(e) }));

    fetchSocialParams()
      .then((d) => {
        setSocialParams({ data: d, loading: false });
        setLocalParams(d);
      })
      .catch((e) => setSocialParams({ loading: false, error: String(e) }));
  }, []);

  const handleSaveParams = async () => {
    if (!localParams) return;

    try {
      const updated = await updateSocialParams(localParams);
      setSocialParams({ data: updated, loading: false });
      setEditingParams(false);
    } catch (error) {
      console.error("Failed to update social params:", error);
    }
  };

  const handleCancelEdit = () => {
    setLocalParams(socialParams.data ?? null);
    setEditingParams(false);
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">Advanced Navigation</h1>
        <p className="text-sm text-neutral-400">
          Social-aware path planning, dynamic obstacle avoidance, and context-adaptive navigation.
        </p>
      </header>

      {/* Module Info Cards */}
      {info.data && (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <InfoCard
            title="Active Goals"
            value={info.data.statistics.active_goals}
            subtitle="navigation goals"
            color="sky"
          />
          <InfoCard
            title="Planned Paths"
            value={info.data.statistics.planned_paths}
            subtitle="path plans"
            color="emerald"
          />
          <InfoCard
            title="Tracked Robots"
            value={info.data.statistics.tracked_robots}
            subtitle="robots navigating"
            color="amber"
          />
          <InfoCard
            title="Total Obstacles"
            value={info.data.statistics.total_obstacles}
            subtitle="detected obstacles"
            color="red"
          />
        </section>
      )}

      {/* Planning Modes & Strategies */}
      {info.data && (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
            <h2 className="mb-3 text-sm font-semibold text-neutral-300">Path Planning Modes</h2>
            <div className="flex flex-wrap gap-2">
              {info.data.planning_modes.map((mode) => (
                <span
                  key={mode}
                  className="rounded-full bg-sky-900/60 px-3 py-1 text-[10px] font-medium text-sky-300"
                >
                  {mode.toUpperCase()}
                </span>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-neutral-500">
              Supported path planning algorithms for various navigation scenarios.
            </p>
          </div>

          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
            <h2 className="mb-3 text-sm font-semibold text-neutral-300">Avoidance Strategies</h2>
            <div className="flex flex-wrap gap-2">
              {info.data.avoidance_strategies.map((strategy) => (
                <span
                  key={strategy}
                  className="rounded-full bg-emerald-900/60 px-3 py-1 text-[10px] font-medium text-emerald-300"
                >
                  {strategy.toUpperCase()}
                </span>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-neutral-500">
              Dynamic obstacle avoidance strategies for safe navigation.
            </p>
          </div>
        </section>
      )}

      {/* Supported Contexts */}
      {info.data && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-neutral-300">Supported Contexts</h2>
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
            <div className="flex flex-wrap gap-2">
              {info.data.supported_contexts.map((context) => (
                <ContextBadge key={context} context={context as NavigationContext} />
              ))}
            </div>
            <p className="mt-3 text-[11px] text-neutral-500">
              Navigation parameters automatically adapt to these environmental contexts.
            </p>
          </div>
        </section>
      )}

      {/* Social Navigation Parameters */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-300">Social Navigation Parameters</h2>
          {!editingParams ? (
            <button
              onClick={() => setEditingParams(true)}
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1 text-xs text-neutral-300 hover:border-sky-500"
            >
              Edit Parameters
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={handleCancelEdit}
                className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1 text-xs text-neutral-300 hover:border-red-500"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveParams}
                className="rounded-lg border border-emerald-700 bg-emerald-900 px-3 py-1 text-xs text-emerald-300 hover:border-emerald-500"
              >
                Save
              </button>
            </div>
          )}
        </div>

        {socialParams.loading && (
          <div className="text-xs text-neutral-400">Loading parameters...</div>
        )}

        {socialParams.error && (
          <div className="text-xs text-red-400">{socialParams.error}</div>
        )}

        {localParams && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Personal Space Zones */}
            <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
              <h3 className="mb-3 text-xs font-semibold text-neutral-300">Personal Space Zones (m)</h3>
              <div className="flex flex-col gap-3">
                <ParamInput
                  label="Intimate Zone"
                  value={localParams.intimate_zone_radius}
                  onChange={(v) => setLocalParams({ ...localParams, intimate_zone_radius: v })}
                  disabled={!editingParams}
                  min={0.1}
                  max={2.0}
                  step={0.1}
                />
                <ParamInput
                  label="Personal Zone"
                  value={localParams.personal_zone_radius}
                  onChange={(v) => setLocalParams({ ...localParams, personal_zone_radius: v })}
                  disabled={!editingParams}
                  min={0.5}
                  max={3.0}
                  step={0.1}
                />
                <ParamInput
                  label="Social Zone"
                  value={localParams.social_zone_radius}
                  onChange={(v) => setLocalParams({ ...localParams, social_zone_radius: v })}
                  disabled={!editingParams}
                  min={1.0}
                  max={5.0}
                  step={0.1}
                />
              </div>
            </div>

            {/* Behavior Weights */}
            <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
              <h3 className="mb-3 text-xs font-semibold text-neutral-300">Behavior Weights (0-1)</h3>
              <div className="flex flex-col gap-3">
                <ParamInput
                  label="Efficiency Weight"
                  value={localParams.efficiency_weight}
                  onChange={(v) => setLocalParams({ ...localParams, efficiency_weight: v })}
                  disabled={!editingParams}
                  min={0}
                  max={1}
                  step={0.1}
                />
                <ParamInput
                  label="Safety Weight"
                  value={localParams.safety_weight}
                  onChange={(v) => setLocalParams({ ...localParams, safety_weight: v })}
                  disabled={!editingParams}
                  min={0}
                  max={1}
                  step={0.1}
                />
                <ParamInput
                  label="Comfort Weight"
                  value={localParams.comfort_weight}
                  onChange={(v) => setLocalParams({ ...localParams, comfort_weight: v })}
                  disabled={!editingParams}
                  min={0}
                  max={1}
                  step={0.1}
                />
              </div>
            </div>

            {/* Crowd Handling */}
            <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
              <h3 className="mb-3 text-xs font-semibold text-neutral-300">Crowd Handling</h3>
              <div className="flex flex-col gap-3">
                <ParamInput
                  label="Max Crowd Density (people/m²)"
                  value={localParams.max_crowd_density}
                  onChange={(v) => setLocalParams({ ...localParams, max_crowd_density: v })}
                  disabled={!editingParams}
                  min={0.1}
                  max={2.0}
                  step={0.1}
                />
                <ParamInput
                  label="Crowd Avoidance Margin (m)"
                  value={localParams.crowd_avoidance_margin}
                  onChange={(v) => setLocalParams({ ...localParams, crowd_avoidance_margin: v })}
                  disabled={!editingParams}
                  min={0.1}
                  max={2.0}
                  step={0.1}
                />
              </div>
            </div>

            {/* Approach Behavior */}
            <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
              <h3 className="mb-3 text-xs font-semibold text-neutral-300">Approach Behavior</h3>
              <div className="flex flex-col gap-3">
                <ParamInput
                  label="Approach Angle (degrees)"
                  value={localParams.approach_angle_deg}
                  onChange={(v) => setLocalParams({ ...localParams, approach_angle_deg: v })}
                  disabled={!editingParams}
                  min={0}
                  max={180}
                  step={5}
                />
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] text-neutral-400">Passing Side Preference</label>
                  <select
                    value={localParams.passing_side_preference}
                    onChange={(e) => setLocalParams({ ...localParams, passing_side_preference: e.target.value })}
                    disabled={!editingParams}
                    className="rounded-lg border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 disabled:opacity-50"
                  >
                    <option value="right">Right</option>
                    <option value="left">Left</option>
                    <option value="adaptive">Adaptive</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Path Visualization Placeholder */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-neutral-300">Path Visualization</h2>
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-4">
          <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-neutral-700/70 text-xs text-neutral-500">
            2D Path Viewer Placeholder – Real-time path and obstacle visualization coming soon
          </div>
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

type InfoCardProps = {
  title: string;
  value: number;
  subtitle: string;
  color: "emerald" | "amber" | "red" | "sky";
};

function InfoCard({ title, value, subtitle, color }: InfoCardProps) {
  const colorClasses = {
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    red: "text-red-400",
    sky: "text-sky-400",
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

function ContextBadge({ context }: { context: NavigationContext }) {
  const contextIcons: Record<NavigationContext, string> = {
    hospital: "🏥",
    warehouse: "🏭",
    office: "🏢",
    street: "🛣️",
    mall: "🏬",
    factory: "🏭",
    home: "🏠",
    outdoor: "🌳",
  };

  return (
    <span className="flex items-center gap-1 rounded-full bg-neutral-800 px-3 py-1.5 text-[11px] font-medium text-neutral-200">
      <span>{contextIcons[context]}</span>
      <span>{context.charAt(0).toUpperCase() + context.slice(1)}</span>
    </span>
  );
}

type ParamInputProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  disabled: boolean;
  min: number;
  max: number;
  step: number;
};

function ParamInput({ label, value, onChange, disabled, min, max, step }: ParamInputProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <label className="text-[11px] text-neutral-400">{label}</label>
        <span className="text-xs font-semibold text-neutral-200">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        className="h-1 w-full appearance-none rounded-full bg-neutral-700 disabled:opacity-50 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-sky-500"
      />
    </div>
  );
}
