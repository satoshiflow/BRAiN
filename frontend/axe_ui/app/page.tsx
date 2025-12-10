"use client";

import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
};

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export default function Page() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <div className="flex flex-1 flex-col">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">BRAiN AXE UI</h1>
        <p className="text-sm text-slate-400">
          Minimaler Chat/Status-Client gegen BRAiN Core API
        </p>
      </header>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="text-sm text-slate-400">Core Health</div>
        <div className="mt-2 text-lg font-semibold">
          {health && health.status === "ok" && <span className="text-emerald-400">ok</span>}
          {error && <span className="text-rose-400">Error: {error}</span>}
          {!health && !error && <span className="text-slate-500">Loading…</span>}
        </div>
      </section>
    </div>
  );
}
