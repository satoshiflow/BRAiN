"use client";

import { useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

type MissionLogEntry = {
  timestamp: number;
  level: string;
  message: string;
  data: Record<string, unknown>;
};

type MissionLogResponse = {
  mission_id: string;
  log: MissionLogEntry[];
};

type Props = {
  missionId: string;
};

export function MissionLogPanel({ missionId }: Props) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<MissionLogEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || entries !== null || loading) return;

    async function loadLogs() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/missions/${missionId}/log`, {
          headers: {
            Accept: "application/json",
          },
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`API error ${res.status}: ${text}`);
        }

        const data: MissionLogResponse = await res.json();
        setEntries(data.log);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Fehler beim Laden der Logs."
        );
      } finally {
        setLoading(false);
      }
    }

    loadLogs();
  }, [open, entries, loading, missionId]);

  return (
    <div className="mt-2 w-full text-xs">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] text-slate-200 hover:border-emerald-500"
      >
        {open ? "Logs ausblenden" : "Logs anzeigen"}
      </button>

      {open && (
        <div className="mt-2 max-h-48 overflow-auto rounded-md border border-slate-800 bg-slate-950/60 p-2">
          {loading && (
            <div className="text-[11px] text-slate-400">Lade Logs...</div>
          )}
          {error && (
            <div className="text-[11px] text-rose-400">
              Fehler beim Laden: {error}
            </div>
          )}
          {!loading && !error && entries && entries.length === 0 && (
            <div className="text-[11px] text-slate-500">
              Keine Log-Einträge vorhanden.
            </div>
          )}
          {!loading && !error && entries && entries.length > 0 && (
            <ul className="space-y-1">
              {entries.map((entry, idx) => (
                <li
                  key={`${entry.timestamp}-${idx}`}
                    className="border-b border-slate-800 pb-1 last:border-0"
                >
                  <div className="text-[10px] text-slate-400">
                    {new Date(entry.timestamp * 1000).toLocaleString()} [{entry.level}]
                    </div>  
                    <div className="text-[11px] text-slate-200">{entry.message}</div>   
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}