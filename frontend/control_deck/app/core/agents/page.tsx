"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import React, { useEffect, useState } from "react";
import Link from "next/link";
import type { AgentSummary } from "@/lib/agentsApi";
import { fetchAgents } from "@/lib/agentsApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export default function CoreAgentsPage() {
  const [state, setState] = useState<LoadState<AgentSummary[]>>({
    loading: true,
  });

  useEffect(() => {
    fetchAgents("system")
      .then((agents) => setState({ data: agents, loading: false }))
      .catch((err) =>
        setState({ loading: false, error: String(err) }),
      );
  }, []);

  return (
    <div className="flex flex-col gap-4 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-white">System Agents</h1>
        <p className="text-sm text-neutral-400">
          Interne BRAiN-Agenten auf System-Level.
        </p>
      </header>

      {state.loading && (
        <div className="text-sm text-neutral-400">Lade System-Agenten…</div>
      )}

      {state.error && (
        <div className="text-sm text-red-400">
          System-Agenten konnten nicht geladen werden:
          <br />
          {state.error}
        </div>
      )}

      {state.data && (
        <div className="overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900/60">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-900/80 border-b border-neutral-800">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Agent
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Type
                </th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-neutral-400">
                  Description
                </th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-neutral-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((agent, idx) => (
                <tr
                  key={agent.id}
                  className={
                    idx % 2 === 0 ? "bg-neutral-950/60" : "bg-neutral-900/40"
                  }
                >
                  <td className="px-4 py-2 align-middle">
                    <div className="text-sm text-white">{agent.label}</div>
                    <div className="text-xs text-neutral-500">{agent.id}</div>
                  </td>
                  <td className="px-4 py-2 align-middle">
                    <span className="inline-flex rounded-full bg-neutral-800 px-2 py-0.5 text-[11px] text-neutral-200">
                      {agent.kind === "system" ? "System" : "User"}
                    </span>
                  </td>
                  <td className="px-4 py-2 align-middle text-xs text-neutral-400">
                    {agent.description ?? "–"}
                  </td>
                  <td className="px-4 py-2 align-middle text-right">
                    <Link
                      href={`/core/agents/${encodeURIComponent(agent.id)}`}
                      className="rounded-full border border-neutral-700 px-3 py-1 text-xs text-neutral-100 hover:bg-neutral-800"
                    >
                      Details
                    </Link>
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