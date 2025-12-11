"use client";

import { useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

type MissionStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

type Props = {
  missionId: string;
  currentStatus: MissionStatus | string;
};

export function MissionStatusControl({ missionId, currentStatus }: Props) {
  const [status, setStatus] = useState<MissionStatus | string>(currentStatus);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function updateStatus(newStatus: MissionStatus) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/missions/${missionId}/status?mission_status=${encodeURIComponent(
          newStatus
        )}`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text}`);
      }

      setStatus(newStatus);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Fehler beim Aktualisieren."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-slate-400">
          {status}
        </span>
        <select
          disabled={loading}
          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-100 outline-none focus:border-emerald-500"
          value={status}
          onChange={(e) => updateStatus(e.target.value as MissionStatus)}
        >
          <option value="PENDING">PENDING</option>
          <option value="RUNNING">RUNNING</option>
          <option value="COMPLETED">COMPLETED</option>
          <option value="FAILED">FAILED</option>
          <option value="CANCELLED">CANCELLED</option>
        </select>
      </div>
      {error && <span className="text-[10px] text-rose-400">{error}</span>}
    </div>
  );
}