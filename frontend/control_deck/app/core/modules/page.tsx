"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useEffect, useState } from "react";
import type { UIModuleManifest } from "@/lib/coreOverviewApi";
import { fetchModuleManifests } from "@/lib/coreOverviewApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function CoreModulesPage() {
  const [state, setState] = useState<LoadState<UIModuleManifest[]>>({
    loading: true,
  });

  useEffect(() => {
    fetchModuleManifests()
      .then((mods) => setState({ data: mods, loading: false }))
      .catch((err) =>
        setState({ loading: false, error: String(err) }),
      );
  }, []);

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">Core Modules</h1>
        <p className="text-sm text-neutral-400">
          Live aus <code>/api/core/modules</code>.
        </p>
      </header>

      {state.loading && (
        <div className="text-sm text-neutral-400">Lade Module…</div>
      )}

      {state.error && (
        <div className="text-sm text-red-400">
          Module konnten nicht geladen werden:
          <br />
          {state.error}
        </div>
      )}

      {!state.loading && state.data && (
        <div className="overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900/60">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-900/80 border-b border-neutral-800">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Name
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Group
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Version
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Status
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Routes
                </th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((mod, idx) => (
                <tr
                  key={mod.name}
                  className={
                    idx % 2 === 0 ? "bg-neutral-950/60" : "bg-neutral-900/40"
                  }
                >
                  <td className="px-4 py-2 align-middle">
                    <div className="text-sm text-white">{mod.label}</div>
                    <div className="text-xs text-neutral-500">{mod.name}</div>
                  </td>

                  <td className="px-4 py-2 align-middle">
                    <span className="text-xs text-neutral-300">
                      {mod.category ?? "Core"}
                    </span>
                  </td>

                  <td className="px-4 py-2 align-middle text-xs text-neutral-300">
                    {mod.version ?? "1.0.0"}
                  </td>

                  <td className="px-4 py-2 align-middle">
                    <span className="inline-flex rounded-full bg-emerald-900/60 px-2 py-0.5 text-[11px] text-emerald-300">
                      STABLE
                    </span>
                  </td>

                  <td className="px-4 py-2 align-middle text-xs text-neutral-300">
                    {mod.routes?.length ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}