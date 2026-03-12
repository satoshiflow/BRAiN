"use client";

import { useCallback, useEffect, useState } from "react";
import { getApiBase } from "@/lib/config";
import {
  getAxeProviderRuntime,
  updateAxeProviderRuntime,
} from "@/lib/api";
import type { AxeProvider, AxeProviderRuntimeResponse } from "@/lib/contracts";

export default function SettingsPage() {
  const [apiBase, setApiBase] = useState(
    getApiBase()
  );
  const [refreshInterval, setRefreshInterval] = useState("10");
  const [theme, setTheme] = useState("dark");
  const [notifications, setNotifications] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [providerRuntime, setProviderRuntime] = useState<AxeProviderRuntimeResponse | null>(null);
  const [providerSelection, setProviderSelection] = useState<AxeProvider>("mock");
  const [runtimeLoading, setRuntimeLoading] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState("");

  const loadRuntime = useCallback(async (token?: string) => {
    try {
      setRuntimeLoading(true);
      setRuntimeError(null);
      const runtime = await getAxeProviderRuntime(
        token ? { Authorization: `Bearer ${token}` } : undefined
      );
      setProviderRuntime(runtime);
      setProviderSelection(runtime.provider);
    } catch (error) {
      setRuntimeError(error instanceof Error ? error.message : "Could not load provider runtime");
    } finally {
      setRuntimeLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRuntime();
    // Do not persist admin token to localStorage for security reasons.
  }, [loadRuntime]);

  const handleSave = () => {
    localStorage.setItem("axe_settings", JSON.stringify({
      apiBase,
      refreshInterval,
      theme,
      notifications,
      autoScroll,
    }));
    alert("Settings saved successfully!");
  };

  const applyProviderSelection = async () => {
    const confirmed = window.confirm(
      `Switch provider runtime to '${providerSelection}'? This affects all active AXE chats.`
    );
    if (!confirmed) {
      return;
    }

    try {
      setRuntimeLoading(true);
      setRuntimeError(null);
      const updated = await updateAxeProviderRuntime(
        { provider: providerSelection },
        adminToken ? { Authorization: `Bearer ${adminToken}` } : undefined
      );
      setProviderRuntime(updated);
      alert(`Provider switched to ${updated.provider}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Provider switch failed";
      setRuntimeError(message);
      alert(`Provider switch failed: ${message}`);
    } finally {
      setRuntimeLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-cyan-300/70">Runtime Control Surface</p>
        <h1 className="axe-surface-title text-3xl font-bold text-white">AXE Configuration</h1>
        <p className="mt-2 text-slate-400">Tune connectivity, provider runtime, and operator interface behavior.</p>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">API Channel</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Backend API URL
            </label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full rounded-lg border border-cyan-500/25 bg-slate-900/70 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="http://localhost:8000"
            />
            <p className="text-xs text-slate-500 mt-1">
              The base URL for the BRAiN backend API
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Refresh Interval (seconds)
            </label>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(e.target.value)}
              className="w-full rounded-lg border border-cyan-500/25 bg-slate-900/70 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
            >
              <option value="5">5 seconds</option>
              <option value="10">10 seconds</option>
              <option value="30">30 seconds</option>
              <option value="60">1 minute</option>
            </select>
            <p className="text-xs text-slate-500 mt-1">
              How often to refresh dashboard data
            </p>
          </div>
        </div>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">Provider Runtime</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Admin Bearer Token (required for runtime change)
            </label>
            <input
              type="password"
              value={adminToken}
              onChange={(e) => setAdminToken(e.target.value)}
              className="w-full rounded-lg border border-cyan-500/25 bg-slate-900/70 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="eyJ..."
            />
            <p className="text-xs text-amber-300 mt-2">
              Security note: token is kept in memory only and is not persisted in localStorage.
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => void loadRuntime(adminToken)}
                className="rounded border border-cyan-500/25 bg-slate-900/75 px-3 py-1.5 text-xs text-cyan-100 hover:bg-slate-800"
              >
                Load runtime
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdminToken("");
                  setProviderRuntime(null);
                  setRuntimeError(null);
                }}
                className="rounded border border-cyan-500/25 bg-slate-900/75 px-3 py-1.5 text-xs text-cyan-100 hover:bg-slate-800"
              >
                Clear token
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Active Provider
            </label>
            <select
              value={providerSelection}
              onChange={(e) => setProviderSelection(e.target.value as AxeProvider)}
              className="w-full rounded-lg border border-cyan-500/25 bg-slate-900/70 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
              disabled={runtimeLoading}
            >
              <option value="groq">Groq</option>
              <option value="ollama">Ollama</option>
              <option value="mock">Mock</option>
            </select>
          </div>

          <button
            onClick={() => void applyProviderSelection()}
            disabled={runtimeLoading}
            className="axe-ring rounded-lg bg-cyan-500/80 px-4 py-2 text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
          >
            {runtimeLoading ? "Applying..." : "Apply Provider"}
          </button>

          {providerRuntime && (
            <div className="rounded-lg border border-cyan-500/25 bg-slate-900/75 p-3 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">Provider</span><span className="text-white font-mono">{providerRuntime.provider}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Model</span><span className="text-white font-mono">{providerRuntime.model}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Sanitization</span><span className="text-white font-mono">{providerRuntime.sanitization_level}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">API Key</span><span className="text-white font-mono">{providerRuntime.api_key_configured ? "configured" : "missing"}</span></div>
            </div>
          )}

          {runtimeError && (
            <p className="text-sm text-red-400">
              {runtimeError}
              {runtimeError.includes("401") ? " (missing/invalid admin token)" : ""}
            </p>
          )}
        </div>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">Interface Preferences</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Theme
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full rounded-lg border border-cyan-500/25 bg-slate-900/70 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="auto">Auto (System)</option>
            </select>
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-500">
          These interface preferences are currently stored locally for the active operator workstation.
        </p>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">Operator Behavior</h2>
        <div className="space-y-4">
          <label className="flex cursor-pointer items-center justify-between rounded-lg border border-cyan-500/15 bg-slate-900/60 px-4 py-3">
            <div>
              <div className="text-sm font-medium text-slate-300">
                Enable Notifications
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Show desktop notifications for important events
              </div>
            </div>
            <input
              type="checkbox"
              checked={notifications}
              onChange={(e) => setNotifications(e.target.checked)}
              className="h-5 w-5 rounded border-slate-700 bg-slate-800 focus:ring-2 focus:ring-cyan-400"
            />
          </label>

          <label className="flex cursor-pointer items-center justify-between rounded-lg border border-cyan-500/15 bg-slate-900/60 px-4 py-3">
            <div>
              <div className="text-sm font-medium text-slate-300">
                Auto-scroll Chat
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Automatically scroll to latest messages in chat
              </div>
            </div>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="h-5 w-5 rounded border-slate-700 bg-slate-800 focus:ring-2 focus:ring-cyan-400"
            />
          </label>
        </div>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">System Information</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Version</span>
            <span className="text-white font-mono">2.0.0</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Build</span>
            <span className="text-white font-mono">2025-12-30</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Framework</span>
            <span className="text-white font-mono">Next.js 14.2.15</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Environment</span>
            <span className="text-white font-mono">
              {process.env.NODE_ENV || "development"}
            </span>
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        <button
          onClick={handleSave}
          className="axe-ring rounded-lg bg-cyan-500/80 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-cyan-400"
        >
          Save Interface Profile
        </button>
        <button
          onClick={() => window.location.reload()}
          className="rounded-lg border border-cyan-500/20 bg-slate-900/70 px-6 py-3 font-medium text-slate-300 transition-colors hover:bg-slate-800"
        >
          Reload Surface Defaults
        </button>
      </div>
    </div>
  );
}
