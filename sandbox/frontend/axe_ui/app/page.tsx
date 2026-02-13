"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type HealthResponse = {
  status: string;
};

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12">
        <div className="w-24 h-24 bg-blue-600 rounded-full mx-auto mb-6 flex items-center justify-center text-5xl">
          🤖
        </div>
        <h1 className="text-5xl font-bold text-white mb-4">
          Welcome to AXE
        </h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
          Auxiliary Execution Engine - Your intelligent assistant for system management,
          agent coordination, and conversational interactions
        </p>
      </div>

      {/* System Status */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">System Status</h2>
            <p className="text-sm text-slate-400 mt-1">BRAiN Core API Connection</p>
          </div>
          <div className="flex items-center gap-3">
            {health && health.status === "ok" && (
              <>
                <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
                <span className="text-green-400 font-semibold">Operational</span>
              </>
            )}
            {error && (
              <>
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="text-red-400 font-semibold">Disconnected</span>
              </>
            )}
            {!health && !error && (
              <>
                <div className="w-3 h-3 rounded-full bg-yellow-500 animate-pulse"></div>
                <span className="text-yellow-400 font-semibold">Connecting...</span>
              </>
            )}
          </div>
        </div>
        {error && (
          <div className="mt-4 p-3 bg-red-900/20 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FeatureCard
          icon="📊"
          title="Dashboard"
          description="Monitor system metrics, agent status, and mission progress in real-time"
          href="/dashboard"
          color="blue"
        />
        <FeatureCard
          icon="💬"
          title="Chat"
          description="Interact with AXE agent using natural language for commands and queries"
          href="/chat"
          color="purple"
        />
        <FeatureCard
          icon="🤖"
          title="Agent Fleet"
          description="View and manage all constitutional agents in the BRAiN ecosystem"
          href="/agents"
          color="green"
        />
        <FeatureCard
          icon="⚙️"
          title="Settings"
          description="Configure API connections, appearance, and behavior preferences"
          href="/settings"
          color="yellow"
        />
      </div>

      {/* Quick Info */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">About AXE</h2>
        <div className="space-y-3 text-sm text-slate-300">
          <p>
            <strong className="text-white">AXE (Auxiliary Execution Engine)</strong> is a
            conversational assistant and system management interface for the BRAiN
            Constitutional AI Framework.
          </p>
          <p>
            It provides safe command execution, log analysis, system monitoring, and
            human-in-the-loop workflows for managing AI agents with DSGVO and EU AI Act
            compliance.
          </p>
          <div className="pt-3 border-t border-slate-800">
            <p className="text-xs text-slate-400">
              Version 2.0.0 • Build 2025-12-30 • Next.js 14.2.15
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
  href,
  color,
}: {
  icon: string;
  title: string;
  description: string;
  href: string;
  color: "blue" | "purple" | "green" | "yellow";
}) {
  const colorClasses = {
    blue: "border-blue-500/50 hover:border-blue-500 hover:bg-blue-500/10",
    purple: "border-purple-500/50 hover:border-purple-500 hover:bg-purple-500/10",
    green: "border-green-500/50 hover:border-green-500 hover:bg-green-500/10",
    yellow: "border-yellow-500/50 hover:border-yellow-500 hover:bg-yellow-500/10",
  };

  return (
    <Link
      href={href}
      className={`block p-6 bg-slate-900 border rounded-lg transition-all ${colorClasses[color]}`}
    >
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400">{description}</p>
      <div className="mt-4 inline-flex items-center gap-2 text-sm text-blue-400">
        <span>Open</span>
        <span>→</span>
      </div>
    </Link>
  );
}
