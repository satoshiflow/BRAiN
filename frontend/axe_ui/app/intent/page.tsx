"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuthSession } from "@/hooks/useAuthSession";

type IntentResponse = {
  resolution_type: "matched_skill" | "draft_required";
  confidence: number;
  reason: string;
  matched_skill_key?: string | null;
  matched_skill_version?: number | null;
  candidates: Array<{
    skill_key: string;
    version: number;
    score: number;
    reason: string;
  }>;
  draft_suggestion?: {
    suggested_skill_key: string;
    rationale: string;
    recommended_capabilities: string[];
  } | null;
  skill_run?: {
    id: string;
    state: string;
  } | null;
};

export default function IntentPage() {
  const { withAuthRetry } = useAuthSession();
  const [intentText, setIntentText] = useState("");
  const [autoExecute, setAutoExecute] = useState(false);
  const [result, setResult] = useState<IntentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await withAuthRetry((token) =>
        fetch("/api/intent/execute", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            intent_text: intentText,
            auto_execute: autoExecute,
          }),
        })
      );
      if (!response.ok) {
        throw new Error(`Intent endpoint failed (${response.status})`);
      }
      setResult((await response.json()) as IntentResponse);
    } catch (err) {
      console.error(err);
      setError("Intent resolution failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-4 lg:p-8">
      <div className="space-y-1">
        <p className="text-[11px] uppercase tracking-[0.2em] text-cyan-300/70">Intent Surface</p>
        <h1 className="text-3xl font-bold text-white">Intent to Skill Execution</h1>
        <p className="text-sm text-slate-400">
          Resolve intent against active skills first; if no strong match exists, AXE returns a draft recommendation.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-4 rounded-xl border border-cyan-500/25 bg-slate-900/70 p-4">
        <textarea
          value={intentText}
          onChange={(event) => setIntentText(event.target.value)}
          placeholder="Describe your problem or mission intent"
          rows={5}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={autoExecute}
            onChange={(event) => setAutoExecute(event.target.checked)}
          />
          Auto execute matched skill
        </label>
        <button
          type="submit"
          disabled={loading || !intentText.trim()}
          className="rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 disabled:opacity-50"
        >
          {loading ? "Resolving..." : "Resolve Intent"}
        </button>
      </form>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      {result ? (
        <div className="space-y-3 rounded-xl border border-cyan-500/20 bg-slate-900/60 p-4 text-sm text-slate-200">
          <p>
            Resolution: <strong>{result.resolution_type}</strong> ({Math.round(result.confidence * 100)}%)
          </p>
          <p>{result.reason}</p>
          <p>
            Matched Skill: <strong>{result.matched_skill_key || "-"}</strong>
          </p>
          {result.skill_run?.id ? (
            <p>
              SkillRun: <strong>{result.skill_run.id}</strong>
            </p>
          ) : null}
          {(result.candidates || []).length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-400">Candidates</p>
              {result.candidates.map((candidate) => (
                <div key={`${candidate.skill_key}-${candidate.version}`} className="rounded border border-slate-700 px-3 py-2">
                  <p>
                    {candidate.skill_key} v{candidate.version} - {Math.round(candidate.score * 100)}%
                  </p>
                </div>
              ))}
            </div>
          ) : null}
          {result.draft_suggestion ? (
            <div className="rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-amber-100">
              Draft suggestion: {result.draft_suggestion.suggested_skill_key}
            </div>
          ) : null}
        </div>
      ) : null}

      <Link href="/chat" className="inline-block text-sm text-cyan-300 hover:underline">
        Back to Chat
      </Link>
    </div>
  );
}
