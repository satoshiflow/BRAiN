// frontend/brain_control_ui/app/brain/debug/page.tsx
"use client";

import { useState } from "react";

const BRAIN_BASE =
  (process.env.NEXT_PUBLIC_BRAIN_API_BASE_URL || "http://localhost:8000")
    .replace(/\/+$/, ""); // trailing Slash entfernen

const AXE_BASE =
  (process.env.NEXT_PUBLIC_AXE_API_BASE ||
    `${BRAIN_BASE}/api/axe`).replace(/\/+$/, "");

type JsonValue = any;

async function getJson(url: string, setError: (msg: string | null) => void) {
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return (await res.json()) as JsonValue;
  } catch (e: any) {
    setError(e.message ?? String(e));
    return null;
  }
}

export default function BrainDebugPage() {
  const [health, setHealth] = useState<JsonValue | null>(null);
  const [missionsInfo, setMissionsInfo] = useState<JsonValue | null>(null);
  const [connectors, setConnectors] = useState<JsonValue | null>(null);
  const [agentsInfo, setAgentsInfo] = useState<JsonValue | null>(null);
  const [axeInfo, setAxeInfo] = useState<JsonValue | null>(null);
  const [axeResponse, setAxeResponse] = useState<string | null>(null);

  const [globalError, setGlobalError] = useState<string | null>(null);
  const [axeError, setAxeError] = useState<string | null>(null);

  const [axeMessage, setAxeMessage] = useState("Hello from BRAIN UI");
  const [axeMetadata, setAxeMetadata] = useState(
    JSON.stringify({ source: "brain_debug_ui", env: "local" }, null, 2)
  );

  const runAll = async () => {
    setGlobalError(null);
    try {
      const h = await getJson(`${BRAIN_BASE}/api/health`, setGlobalError);
      const m = await getJson(
        `${BRAIN_BASE}/api/missions/info`,
        setGlobalError
      );
      const c = await getJson(
        `${BRAIN_BASE}/api/connectors/list`,
        setGlobalError
      );
      const a = await getJson(
        `${BRAIN_BASE}/api/agents/info`,
        setGlobalError
      );
      const ai = await getJson(`${AXE_BASE}/info`, setGlobalError);

      if (h) setHealth(h);
      if (m) setMissionsInfo(m);
      if (c) setConnectors(c);
      if (a) setAgentsInfo(a);
      if (ai) setAxeInfo(ai);
    } catch (e: any) {
      setGlobalError(e.message ?? String(e));
    }
  };

  const sendToAxe = async () => {
    setAxeError(null);
    setAxeResponse(null);
    let meta: any = {};
    try {
      meta = JSON.parse(axeMetadata || "{}");
    } catch {
      setAxeError("Metadata ist kein gültiges JSON.");
      return;
    }

    try {
      const res = await fetch(`${AXE_BASE}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: axeMessage,
          metadata: meta,
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const data = await res.json();
      setAxeResponse(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setAxeError(e.message ?? String(e));
    }
  };

  return (
    <main className="min-h-screen bg-white text-black p-4">
      <h1>BRAiN Debug Console</h1>
      <p>
        Live-Integrationstest zwischen BRAIN Control Center und Backend
        (Missions, Connectors, Agents, AXE).
      </p>

      <button onClick={runAll}>▶ Run All Checks</button>
      {globalError && (
        <p style={{ color: "red" }}>
          Global Error: {globalError}
        </p>
      )}

      <h2>Backend Health</h2>
      <button
        onClick={async () => {
          const h = await getJson(`${BRAIN_BASE}/api/health`, setGlobalError);
          if (h) setHealth(h);
        }}
      >
        Test
      </button>
      <pre>{health && JSON.stringify(health, null, 2)}</pre>

      <h2>Mission System</h2>
      <button
        onClick={async () => {
          const m = await getJson(
            `${BRAIN_BASE}/api/missions/info`,
            setGlobalError
          );
          if (m) setMissionsInfo(m);
        }}
      >
        /api/missions/info
      </button>
      <pre>{missionsInfo && JSON.stringify(missionsInfo, null, 2)}</pre>

      <h2>Connectors</h2>
      <button
        onClick={async () => {
          const c = await getJson(
            `${BRAIN_BASE}/api/connectors/list`,
            setGlobalError
          );
          if (c) setConnectors(c);
        }}
      >
        /api/connectors/list
      </button>
      <pre>{connectors && JSON.stringify(connectors, null, 2)}</pre>

      <h2>Agents</h2>
      <button
        onClick={async () => {
          const a = await getJson(
            `${BRAIN_BASE}/api/agents/info`,
            setGlobalError
          );
          if (a) setAgentsInfo(a);
        }}
      >
        /api/agents/info
      </button>
      <pre>{agentsInfo && JSON.stringify(agentsInfo, null, 2)}</pre>

      <h2>AXE Info</h2>
      <button
        onClick={async () => {
          const ai = await getJson(`${AXE_BASE}/info`, setGlobalError);
          if (ai) setAxeInfo(ai);
        }}
      >
        /api/axe/info
      </button>
      <pre>{axeInfo && JSON.stringify(axeInfo, null, 2)}</pre>

      <h2>AXE Console</h2>
      <div style={{ display: "flex", gap: "1rem" }}>
        <div>
          <label>Message</label>
          <br />
          <textarea
            rows={4}
            cols={30}
            value={axeMessage}
            onChange={(e) => setAxeMessage(e.target.value)}
          />
        </div>
        <div>
          <label>Metadata (JSON)</label>
          <br />
          <textarea
            rows={4}
            cols={30}
            value={axeMetadata}
            onChange={(e) => setAxeMetadata(e.target.value)}
          />
        </div>
      </div>
      <button onClick={sendToAxe}>▶ Send to AXE</button>
      {axeError && <p style={{ color: "red" }}>Error: {axeError}</p>}
      {axeResponse && <pre>{axeResponse}</pre>}
    </main>
  );
}