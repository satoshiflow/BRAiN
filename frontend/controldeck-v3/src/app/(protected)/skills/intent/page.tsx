"use client";

import Link from "next/link";
import { useState } from "react";

import { intentApi, type IntentExecuteResponse } from "@/lib/api/intent";

export default function SkillsIntentPage() {
  const [intentText, setIntentText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [problemStatement, setProblemStatement] = useState("");
  const [autoExecute, setAutoExecute] = useState(false);
  const [minConfidence, setMinConfidence] = useState(0.2);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<IntentExecuteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await intentApi.execute({
        intent_text: intentText || undefined,
        source_url: sourceUrl || undefined,
        problem_statement: problemStatement || undefined,
        auto_execute: autoExecute,
        min_confidence: minConfidence,
      });
      setResult(response);
    } catch (err) {
      console.error("Intent execution failed", err);
      setError("Intent konnte nicht verarbeitet werden");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Link href="/skills" className="text-sm text-blue-600 hover:underline">
          Zurueck zu Skills
        </Link>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Intent to Skill</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Problem-Statement oder URL eingeben, bestehenden Skill matchen und optional direkt ausfuehren.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Intent Text</label>
          <textarea
            value={intentText}
            onChange={(event) => setIntentText(event.target.value)}
            rows={4}
            className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            placeholder="z.B. Search knowledge about recurring outage incidents"
          />
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Source URL</label>
            <input
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              placeholder="https://..."
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Problem Statement</label>
            <input
              value={problemStatement}
              onChange={(event) => setProblemStatement(event.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              placeholder="Kurzproblem fuer Routing"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={autoExecute}
              onChange={(event) => setAutoExecute(event.target.checked)}
            />
            Auto Execute
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            Min Confidence
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={(event) => setMinConfidence(Number(event.target.value) || 0)}
              className="w-20 rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
          </label>
          <button
            type="submit"
            disabled={isLoading}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isLoading ? "Verarbeite..." : "Intent ausfuehren"}
          </button>
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-sm text-slate-600 dark:text-slate-400">{result.reason}</p>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">Resolution</p>
              <p className="font-medium text-slate-900 dark:text-slate-100">{result.resolution_type}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">Confidence</p>
              <p className="font-medium text-slate-900 dark:text-slate-100">{Math.round(result.confidence * 100)}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">Matched Skill</p>
              <p className="font-medium text-slate-900 dark:text-slate-100">{result.matched_skill_key || "-"}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">Run</p>
              <p className="font-medium text-slate-900 dark:text-slate-100">{result.skill_run?.id?.slice(0, 8) || "-"}</p>
            </div>
          </div>

          {(result.candidates || []).length > 0 && (
            <div>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Candidates</h2>
              <div className="space-y-2">
                {result.candidates.map((candidate) => (
                  <div key={`${candidate.skill_key}-${candidate.version}`} className="rounded border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                    <p className="font-medium text-slate-900 dark:text-slate-100">
                      {candidate.skill_key} v{candidate.version}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Score {Math.round(candidate.score * 100)}% - {candidate.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.cognitive_assessment && (
            <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-900/60 dark:bg-emerald-950/20">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
                Cognitive Assessment
              </h2>
              <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                <div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Confidence</p>
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {Math.round(result.cognitive_assessment.evaluation.confidence * 100)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Novelty</p>
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {Math.round(result.cognitive_assessment.evaluation.novelty_score * 100)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Impact</p>
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {Math.round(result.cognitive_assessment.evaluation.impact_score * 100)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Associated Cases</p>
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {result.cognitive_assessment.association.total_cases}
                  </p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Perception</p>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    {result.cognitive_assessment.perception.normalized_intent}
                  </p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Governance Hints</p>
                  <div className="flex flex-wrap gap-2">
                    {(result.cognitive_assessment.evaluation.governance_hints.length > 0
                      ? result.cognitive_assessment.evaluation.governance_hints
                      : ["none"]).map((hint) => (
                      <span key={hint} className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                        {hint}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Memory Cases</p>
                  <div className="space-y-2">
                    {(result.cognitive_assessment.association.memory_cases || []).slice(0, 3).map((item) => (
                      <div key={item.source_id} className="rounded border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
                        <p className="font-medium text-slate-900 dark:text-slate-100">{item.title}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{item.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Knowledge Cases</p>
                  <div className="space-y-2">
                    {(result.cognitive_assessment.association.knowledge_cases || []).slice(0, 3).map((item) => (
                      <div key={item.source_id} className="rounded border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
                        <p className="font-medium text-slate-900 dark:text-slate-100">{item.title}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{item.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
