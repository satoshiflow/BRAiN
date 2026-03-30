"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  skillsApi,
  type SkillLifecycleAnalyticsResponse,
  type SkillMarketplaceRankingResponse,
} from "@/lib/api/skills";
import { formatRelativeTime } from "@/lib/utils";

function asPercent(value: number): string {
  return `${Math.round((value || 0) * 100)}%`;
}

export default function SkillsAnalyticsPage() {
  const [analytics, setAnalytics] = useState<SkillLifecycleAnalyticsResponse | null>(null);
  const [ranking, setRanking] = useState<SkillMarketplaceRankingResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [analyticsPayload, rankingPayload] = await Promise.all([
          skillsApi.getLifecycleAnalytics(30, 100),
          skillsApi.getMarketplaceRanking(30, 25),
        ]);
        if (!active) {
          return;
        }
        setAnalytics(analyticsPayload);
        setRanking(rankingPayload);
        setError(null);
      } catch (err) {
        console.error("Failed to load skill analytics", err);
        if (!active) {
          return;
        }
        setError("Skill Analytics konnten nicht geladen werden");
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
  }, []);

  if (isLoading) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Lade Skill Analytics...</p>;
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/skills" className="text-sm text-blue-600 hover:underline">
          Zurueck zu Skills
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/skills" className="text-sm text-blue-600 hover:underline">
            Zurueck zu Skills
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">Skill Value Lifecycle Analytics</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Aggregierte Performance- und Value-Signale der letzten {analytics?.summary.window_days || 30} Tage.
          </p>
        </div>
      </div>

      {analytics && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Skills</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{analytics.summary.total_skills}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Runs (Window)</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{analytics.summary.total_runs}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Avg Value Score</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{asPercent(analytics.summary.avg_value_score)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">Avg Success Rate</p>
            <p className="text-xl font-semibold text-slate-900 dark:text-slate-100">{asPercent(analytics.summary.avg_success_rate)}</p>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Marketplace Ranking</h2>
        </div>
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          {(ranking?.items || []).length === 0 ? (
            <p className="p-4 text-sm text-slate-500 dark:text-slate-400">Keine Ranking-Daten verfuegbar.</p>
          ) : (
            ranking!.items.map((item) => (
              <div key={`${item.rank}-${item.skill_key}`} className="grid grid-cols-2 gap-3 px-4 py-3 text-xs md:grid-cols-6">
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Rank</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">#{item.rank}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Skill</p>
                  <p className="text-slate-900 dark:text-slate-100">{item.skill_key}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Market Score</p>
                  <p className="text-slate-900 dark:text-slate-100">{asPercent(item.market_score)}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Value</p>
                  <p className="text-slate-900 dark:text-slate-100">{asPercent(item.value_score)}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Success</p>
                  <p className="text-slate-900 dark:text-slate-100">{asPercent(item.success_rate)}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400">Last Run</p>
                  <p className="text-slate-900 dark:text-slate-100">{item.last_run_at ? formatRelativeTime(item.last_run_at) : "-"}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
