"use client";

import Link from "next/link";
import { useMemo, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { skillsApi, type Skill, type SkillRun } from "@/lib/api/skills";
import { formatRelativeTime } from "@/lib/utils";

type ValueScoreState = {
  value_score: number;
  source: string;
  effort_saved_hours: number;
  quality_impact: number;
  complexity_level: string;
  risk_tier: string;
  breakdown?: Record<string, unknown>;
};

type ValueHistoryState = {
  run_id: string;
  skill_version: number;
  state: string;
  created_at: string;
  overall_score?: number | null;
  value_score?: number | null;
  quality_impact?: number | null;
  effort_saved_hours?: number | null;
  source?: string | null;
};

function scoreToPercent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value || 0)) * 100);
}

function BreakdownBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
        <span>{label}</span>
        <span>{scoreToPercent(value)}%</span>
      </div>
      <div className="h-2 rounded bg-slate-200 dark:bg-slate-700">
        <div
          className="h-2 rounded bg-cyan-500"
          style={{ width: `${scoreToPercent(value)}%` }}
        />
      </div>
    </div>
  );
}

export default function SkillDetailPage() {
  const params = useParams<{ skillKey: string }>();
  const skillKey = useMemo(() => decodeURIComponent(params.skillKey || ""), [params.skillKey]);

  const [skill, setSkill] = useState<Skill | null>(null);
  const [versions, setVersions] = useState<Skill[]>([]);
  const [runs, setRuns] = useState<SkillRun[]>([]);
  const [valueHistory, setValueHistory] = useState<ValueHistoryState[]>([]);
  const [valueScore, setValueScore] = useState<ValueScoreState | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const [skills, recentRuns, history] = await Promise.all([
          skillsApi.list("updated_at", skillKey),
          skillsApi.getRuns(25, undefined, skillKey),
          skillsApi.getValueHistory(skillKey, 40),
        ]);

        if (!active) {
          return;
        }

        const orderedVersions = [...skills].sort((a, b) => b.version - a.version);
        const initial = orderedVersions[0] ?? null;
        setVersions(orderedVersions);
        setSkill(initial);
        setSelectedVersion(initial?.version ?? null);
        setRuns(recentRuns);
        setValueHistory(history.items || []);
        setError(null);
      } catch (err) {
        console.error("Failed to load skill detail", err);
        if (!active) {
          return;
        }
        setError("Skill-Details konnten nicht geladen werden");
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [skillKey]);

  useEffect(() => {
    if (!selectedVersion) {
      return;
    }

    let active = true;
    const loadValue = async () => {
      try {
        const value = await skillsApi.getValueScore(skillKey, selectedVersion);
        if (!active) {
          return;
        }
        setValueScore(value);
      } catch (err) {
        console.error("Failed to load value score", err);
      }
    };

    const picked = versions.find((item) => item.version === selectedVersion) || null;
    setSkill(picked);
    setExpandedRunId(null);
    loadValue();

    return () => {
      active = false;
    };
  }, [selectedVersion, versions, skillKey]);

  const filteredRuns = useMemo(() => {
    if (!selectedVersion) {
      return runs;
    }
    return runs.filter((run) => run.skillVersion === selectedVersion);
  }, [runs, selectedVersion]);

  const filteredHistory = useMemo(() => {
    if (!selectedVersion) {
      return valueHistory;
    }
    return valueHistory.filter((item) => item.skill_version === selectedVersion);
  }, [valueHistory, selectedVersion]);

  const breakdown = valueScore?.breakdown || {};
  const effortComponent = Number(breakdown["effort_component"] || 0);
  const qualityComponent = Number(breakdown["quality_component"] || 0);
  const complexityComponent = Number(breakdown["complexity_component"] || 0);
  const computedScore = Number(breakdown["computed_score"] || 0);

  if (isLoading) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Lade Skill-Details...</p>;
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/skills" className="text-sm text-blue-600 hover:underline">
          Zurueck zum Skill-Katalog
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link href="/skills" className="text-sm text-blue-600 hover:underline">
          Zurueck zum Skill-Katalog
        </Link>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{skill?.name || skillKey}</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">Governance-Ansicht fuer Skill, Value-Modell und letzte Ausfuehrungen.</p>
        <div className="pt-2">
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            Version
            <select
              value={selectedVersion ?? ""}
              onChange={(event) => setSelectedVersion(Number(event.target.value) || null)}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              {versions.map((entry) => (
                <option key={entry.version} value={entry.version}>
                  v{entry.version}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {valueScore && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Value Score</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{Math.round(valueScore.value_score * 100)}%</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">Quelle: {valueScore.source}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Effort Saved</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{valueScore.effort_saved_hours.toFixed(1)}h</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Quality Impact</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{Math.round(valueScore.quality_impact * 100)}%</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Complexity / Risk</p>
            <p className="text-xl font-semibold text-slate-900 capitalize dark:text-slate-100">{valueScore.complexity_level}</p>
            <p className="text-xs text-slate-500 capitalize dark:text-slate-400">Risk: {valueScore.risk_tier}</p>
          </div>
        </div>
      )}

      {valueScore && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Value Breakdown</h2>
          <div className="space-y-3">
            <BreakdownBar label="Effort Component" value={effortComponent} />
            <BreakdownBar label="Quality Component" value={qualityComponent} />
            <BreakdownBar label="Complexity Component" value={complexityComponent} />
            <BreakdownBar label="Computed Score" value={computedScore} />
          </div>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Skill-Profil</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Skill Key</p>
            <p className="text-sm text-slate-900 dark:text-slate-100">{skill?.key || skillKey}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Version</p>
            <p className="text-sm text-slate-900 dark:text-slate-100">v{skill?.version ?? "-"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Kategorie</p>
            <p className="text-sm text-slate-900 dark:text-slate-100">{skill?.category || "-"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Status</p>
            <p className="text-sm text-slate-900 dark:text-slate-100">{skill?.isEnabled ? "Aktiv" : "Deaktiviert"}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Letzte SkillRuns</h2>
        </div>
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          {filteredRuns.length === 0 ? (
            <p className="p-4 text-sm text-slate-500 dark:text-slate-400">Keine SkillRuns verfuegbar.</p>
          ) : (
            filteredRuns.map((run) => (
              <div key={run.id} className="px-4 py-3">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 text-left"
                  onClick={() => setExpandedRunId((current) => (current === run.id ? null : run.id))}
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{run.state}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{formatRelativeTime(run.createdAt)}</p>
                  </div>
                  <div className="text-right text-xs text-slate-500 dark:text-slate-400">
                    <p>ID: {run.id.slice(0, 8)}...</p>
                    <p>Version {run.skillVersion}</p>
                  </div>
                </button>
                {expandedRunId === run.id && (
                  <div className="mt-3 space-y-3 rounded border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900">
                    <div>
                      <p className="mb-1 text-xs font-semibold text-slate-600 dark:text-slate-300">Input</p>
                      <pre className="overflow-x-auto text-xs text-slate-700 dark:text-slate-200">{JSON.stringify(run.input, null, 2)}</pre>
                    </div>
                    <div>
                      <p className="mb-1 text-xs font-semibold text-slate-600 dark:text-slate-300">Output</p>
                      <pre className="overflow-x-auto text-xs text-slate-700 dark:text-slate-200">{JSON.stringify(run.output || {}, null, 2)}</pre>
                    </div>
                    {run.error && (
                      <div>
                        <p className="mb-1 text-xs font-semibold text-red-600 dark:text-red-300">Error</p>
                        <pre className="overflow-x-auto text-xs text-red-700 dark:text-red-300">{run.error}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Value Trend</h2>
        </div>
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          {filteredHistory.length === 0 ? (
            <p className="p-4 text-sm text-slate-500 dark:text-slate-400">Noch keine Value-History vorhanden.</p>
          ) : (
            filteredHistory.slice(0, 12).map((item) => (
              <div key={`${item.run_id}-${item.created_at}`} className="grid grid-cols-2 gap-3 px-4 py-3 text-xs sm:grid-cols-5">
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Zeitpunkt</p>
                  <p className="text-slate-800 dark:text-slate-100">{formatRelativeTime(item.created_at)}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">State</p>
                  <p className="capitalize text-slate-800 dark:text-slate-100">{item.state}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Value Score</p>
                  <p className="text-slate-800 dark:text-slate-100">{item.value_score != null ? `${scoreToPercent(item.value_score)}%` : "-"}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Overall</p>
                  <p className="text-slate-800 dark:text-slate-100">{item.overall_score != null ? `${scoreToPercent(item.overall_score)}%` : "-"}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Effort</p>
                  <p className="text-slate-800 dark:text-slate-100">{item.effort_saved_hours != null ? `${item.effort_saved_hours.toFixed(1)}h` : "-"}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
