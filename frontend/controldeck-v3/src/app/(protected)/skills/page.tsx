"use client";

import { useEffect, useState, useCallback } from "react";
import { skillsApi, type Skill, type SkillRun } from "@/lib/api/skills";
import { cn, formatRelativeTime, formatDuration } from "@/lib/utils";
import { HelpHint } from "@/components/help/help-hint";
import { getControlDeckHelpTopic } from "@/lib/help/topics";

function SkillStatusBadge({ isEnabled }: { isEnabled: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        isEnabled
          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
          : "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
      )}
    >
      {isEnabled ? "Aktiv" : "Deaktiviert"}
    </span>
  );
}

function RunStatusBadge({ state }: { state: SkillRun["state"] }) {
  const styles: Record<SkillRun["state"], string> = {
    queued: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    planning: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    running: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    succeeded: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    cancelled: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
    waiting_approval: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    cancel_requested: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    timed_out: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  };

  const labels: Record<SkillRun["state"], string> = {
    queued: "Warteschlange",
    planning: "Planung",
    running: "Läuft",
    succeeded: "Erfolgreich",
    failed: "Fehlgeschlagen",
    cancelled: "Abgebrochen",
    waiting_approval: "Wartet auf Freigabe",
    cancel_requested: "Abbruch angefragt",
    timed_out: "Zeitlimit",
  };

  return (
    <span className={cn("text-xs", styles[state])}>{labels[state]}</span>
  );
}

function SkillDetailModal({
  skill,
  onClose,
  onTrigger,
}: {
  skill: Skill;
  onClose: () => void;
  onTrigger: (skillKey: string) => void;
}) {
  const [isTriggering, setIsTriggering] = useState(false);

  const handleTrigger = async () => {
    setIsTriggering(true);
    try {
      await onTrigger(skill.key);
      onClose();
    } catch (err) {
      console.error("Failed to trigger skill:", err);
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-auto">
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                {skill.name}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {skill.key} • v{skill.version}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18" /><path d="m6 6 12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Beschreibung
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {skill.description}
              </p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Kategorie
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">{skill.category}</p>
            </div>

            {skill.parameters.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Parameter
                </h3>
                <div className="space-y-2">
                  {skill.parameters.map((param) => (
                    <div
                      key={param.name}
                      className="bg-slate-50 dark:bg-slate-900 rounded p-3 text-sm"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {param.name}
                        </span>
                        {param.required && (
                          <span className="text-xs text-red-500">erforderlich</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Typ: {param.type}
                      </p>
                      {param.description && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {param.description}
                        </p>
                      )}
                      {param.default !== undefined && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Standard: {JSON.stringify(param.default)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              Schließen
            </button>
            <button
              onClick={handleTrigger}
              disabled={!skill.isEnabled || isTriggering}
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTriggering ? "Wird ausgeführt..." : "Jetzt ausführen"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RunDetailModal({
  run,
  onClose,
  onRetry,
  onCancel,
}: {
  run: SkillRun;
  onClose: () => void;
  onRetry: (runId: string) => void;
  onCancel: (runId: string) => void;
}) {
  const [isActioning, setIsActioning] = useState(false);

  const handleRetry = async () => {
    setIsActioning(true);
    try {
      await onRetry(run.id);
      onClose();
    } catch (err) {
      console.error("Failed to retry:", err);
    } finally {
      setIsActioning(false);
    }
  };

  const handleCancel = async () => {
    setIsActioning(true);
    try {
      await onCancel(run.id);
      onClose();
    } catch (err) {
      console.error("Failed to cancel:", err);
    } finally {
      setIsActioning(false);
    }
  };

  const duration = run.startedAt && run.completedAt
    ? Math.round((new Date(run.completedAt).getTime() - new Date(run.startedAt).getTime()) / 1000)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                {run.skillKey}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                ID: {run.id}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18" /><path d="m6 6 12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <RunStatusBadge state={run.state} />
              {duration && (
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {formatDuration(duration)}
                </span>
              )}
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {formatRelativeTime(run.createdAt)}
              </span>
            </div>

            <div>
              <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Input
              </h3>
              <pre className="bg-slate-50 dark:bg-slate-900 rounded p-3 text-xs overflow-x-auto">
                {JSON.stringify(run.input, null, 2)}
              </pre>
            </div>

            {run.output && (
              <div>
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Output
                </h3>
                <pre className="bg-slate-50 dark:bg-slate-900 rounded p-3 text-xs overflow-x-auto">
                  {JSON.stringify(run.output, null, 2)}
                </pre>
              </div>
            )}

            {run.error && (
              <div>
                <h3 className="text-sm font-medium text-red-700 dark:text-red-400 mb-2">
                  Fehler
                </h3>
                <pre className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 text-xs overflow-x-auto text-red-600 dark:text-red-400">
                  {run.error}
                </pre>
              </div>
            )}
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              Schließen
            </button>
            {run.state === "failed" && (
              <button
                onClick={handleRetry}
                disabled={isActioning}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isActioning ? "Wird wiederholt..." : "Erneut ausführen"}
              </button>
            )}
            {run.state === "running" && (
              <button
                onClick={handleCancel}
                disabled={isActioning}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {isActioning ? "Wird abgebrochen..." : "Abbrechen"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [runs, setRuns] = useState<SkillRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"skills" | "runs">("skills");
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [selectedRun, setSelectedRun] = useState<SkillRun | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [skillsData, runsData] = await Promise.all([
        skillsApi.list(),
        skillsApi.getRuns(20),
      ]);
      setSkills(skillsData);
      setRuns(runsData);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch skills data:", err);
      setError("Konnte Skills-Daten nicht laden");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleTriggerSkill = async (skillKey: string) => {
    try {
      await skillsApi.trigger({
        skill_key: skillKey,
        input_payload: {},
      });
      const newRuns = await skillsApi.getRuns(20);
      setRuns(newRuns);
    } catch (err) {
      console.error("Failed to trigger skill:", err);
      setError("Skill konnte nicht gestartet werden");
    }
  };

  const handleRetryRun = async (runId: string) => {
    try {
      await skillsApi.retry(runId);
      const newRuns = await skillsApi.getRuns(20);
      setRuns(newRuns);
    } catch (err) {
      console.error("Failed to retry run:", err);
      setError("Wiederholung fehlgeschlagen");
    }
  };

  const handleCancelRun = async (runId: string) => {
    try {
      await skillsApi.cancel(runId);
      const newRuns = await skillsApi.getRuns(20);
      setRuns(newRuns);
    } catch (err) {
      console.error("Failed to cancel run:", err);
      setError("Abbruch fehlgeschlagen");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 dark:text-slate-400">Laden...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Skills</h1>
        {(() => {
          const topic = getControlDeckHelpTopic("skills.catalog");
          return topic ? <HelpHint topic={topic} /> : null;
        })()}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab("skills")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "skills"
              ? "border-blue-600 text-blue-600 dark:text-blue-400"
              : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          )}
        >
          Skill-Katalog ({skills.length})
        </button>
        <button
          onClick={() => setActiveTab("runs")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "runs"
              ? "border-blue-600 text-blue-600 dark:text-blue-400"
              : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          )}
        >
          Letzte Ausführungen ({runs.length})
        </button>
      </div>

      {activeTab === "skills" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skills.length === 0 ? (
            <p className="col-span-full text-center text-slate-500 dark:text-slate-400 py-8">
              Keine Skills verfügbar
            </p>
          ) : (
            skills.map((skill) => (
              <div
                key={skill.key}
                className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer"
                onClick={() => setSelectedSkill(skill)}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium text-slate-900 dark:text-slate-100">
                    {skill.name}
                  </h3>
                  <SkillStatusBadge isEnabled={skill.isEnabled} />
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-3 line-clamp-2">
                  {skill.description}
                </p>
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-500">
                  <span>{skill.category}</span>
                  <span>v{skill.version}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "runs" && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="divide-y divide-slate-200 dark:divide-slate-700">
            {runs.length === 0 ? (
              <p className="p-8 text-center text-slate-500 dark:text-slate-400">
                Keine Ausführungen gefunden
              </p>
            ) : (
              runs.map((run) => (
                <div 
                  key={run.id} 
                  className="p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                  onClick={() => setSelectedRun(run)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <RunStatusBadge state={run.state} />
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {run.skillKey}
                        </span>
                      </div>
                      {run.error && (
                        <p className="text-sm text-red-600 dark:text-red-400 truncate">
                          {run.error}
                        </p>
                      )}
                      <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                        {formatRelativeTime(run.createdAt)}
                      </p>
                    </div>
                    <div className="text-right">
                      {run.startedAt && run.completedAt && (
                        <p className="text-xs text-slate-500 dark:text-slate-500">
                          {Math.round(
                            (new Date(run.completedAt).getTime() -
                              new Date(run.startedAt).getTime()) /
                              1000
                          )}s
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {selectedSkill && (
        <SkillDetailModal
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
          onTrigger={handleTriggerSkill}
        />
      )}

      {selectedRun && (
        <RunDetailModal
          run={selectedRun}
          onClose={() => setSelectedRun(null)}
          onRetry={handleRetryRun}
          onCancel={handleCancelRun}
        />
      )}
    </div>
  );
}
