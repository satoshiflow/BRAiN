"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [apiBase, setApiBase] = useState(
    process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000"
  );
  const [refreshInterval, setRefreshInterval] = useState("10");
  const [theme, setTheme] = useState("dark");
  const [notifications, setNotifications] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);

  const handleSave = () => {
    // Save settings to localStorage or backend
    localStorage.setItem("axe_settings", JSON.stringify({
      apiBase,
      refreshInterval,
      theme,
      notifications,
      autoScroll,
    }));
    alert("Settings saved successfully!");
  };

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 mt-2">Configure AXE UI preferences and connections</p>
      </div>

      {/* API Configuration */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">API Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Backend API URL
            </label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
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

      {/* Appearance */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Appearance</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Theme
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="auto">Auto (System)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Behavior */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Behavior</h2>
        <div className="space-y-4">
          <label className="flex items-center justify-between cursor-pointer">
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
              className="w-5 h-5 bg-slate-800 border-slate-700 rounded focus:ring-2 focus:ring-blue-500"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer">
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
              className="w-5 h-5 bg-slate-800 border-slate-700 rounded focus:ring-2 focus:ring-blue-500"
            />
          </label>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">System Information</h2>
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

      {/* Actions */}
      <div className="flex gap-4">
        <button
          onClick={handleSave}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
        >
          Save Settings
        </button>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-lg border border-slate-700 transition-colors"
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
