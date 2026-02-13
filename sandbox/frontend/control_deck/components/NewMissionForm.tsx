"use client";

import { useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export function NewMissionForm() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!name.trim()) {
      setError("Name darf nicht leer sein.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/missions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          name,
          description: description || null,
          data: {},
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text}`);
      }

      const mission = await res.json();
      setSuccess(`Mission angelegt: ${mission.name} (${mission.id})`);
      setName("");
      setDescription("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unbekannter Fehler beim Anlegen."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
    >
      <div className="mb-3 text-sm font-medium text-slate-200">
        Neue Mission anlegen
      </div>
      <div className="mb-3 grid gap-3 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Name</label>
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-emerald-500"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="z.B. Demo Mission"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Beschreibung</label>
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-emerald-500"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="optional"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={loading}
          className="rounded-md border border-emerald-500 bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading ? "Anlegen..." : "Mission anlegen"}
        </button>
        {error && (
          <span className="text-xs text-rose-400">Fehler: {error}</span>
        )}
        {success && (
          <span className="text-xs text-emerald-400">{success}</span>
        )}
      </div>
      <div className="mt-2 text-xs text-slate-500">
        Nach dem Anlegen bitte die Seite neu laden, um die Mission in der Liste
        zu sehen.
      </div>
    </form>
  );
}
