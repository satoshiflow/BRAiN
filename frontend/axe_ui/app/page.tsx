"use client";

import { useEffect, useState } from "react";
import { getApiBase } from "@/lib/config";
import { getApiHealth } from "@/lib/api";

const API_BASE = getApiBase();

export default function HomePage() {
  const [status, setStatus] = useState("Loading...");
  const [error, setError] = useState<string | null>(null);

  const testConnection = () => {
    setStatus("Testing...");
    setError(null);
    
    getApiHealth()
      .then((data) => {
        if (data.status === "ok") {
          setStatus("Connected ✅ - BRAiN v" + data.version);
        } else {
          setStatus("Unexpected: " + JSON.stringify(data));
        }
      })
      .catch((err) => {
        setStatus("Failed ❌");
        setError(err.message);
      });
  };

  useEffect(() => {
    testConnection();
  }, []);

  return (
    <div style={{ padding: 40, fontFamily: "sans-serif", background: "#0f172a", color: "white", minHeight: "100vh" }}>
      <h1>🤖 AXE UI - BRAiN Gateway</h1>
      <p style={{ color: "#94a3b8" }}>Secure Interface to BRAiN Core</p>
      
      <div style={{ marginTop: 30, padding: 20, background: "#1e293b", borderRadius: 8 }}>
        <p><strong>API:</strong> {API_BASE}</p>
        <p><strong>Status:</strong> <span style={{ 
          color: status.includes("Connected") ? "#4ade80" : status.includes("Failed") ? "#f87171" : "#fbbf24"
        }}>{status}</span></p>
        {error && <p style={{ color: "#f87171", marginTop: 10 }}>Error: {error}</p>}
        <button 
          onClick={testConnection}
          style={{ 
            marginTop: 15, 
            padding: "8px 16px", 
            background: "#3b82f6", 
            color: "white", 
            border: "none", 
            borderRadius: 4,
            cursor: "pointer"
          }}
        >
          Test Connection
        </button>
      </div>
      
      <div style={{ marginTop: 40 }}>
        <a href="/dashboard" style={{ color: "#60a5fa", marginRight: 20 }}>📊 Dashboard</a>
        <a href="/chat" style={{ color: "#60a5fa", marginRight: 20 }}>💬 Chat</a>
        <a href="/agents" style={{ color: "#60a5fa" }}>🤖 Agents</a>
      </div>
      
      <div style={{ marginTop: 40, padding: 20, background: "#1e293b", borderRadius: 8 }}>
        <h3>🛡️ Security Notice</h3>
        <p style={{ color: "#94a3b8", fontSize: 14 }}>
          AXE is the ONLY authorized gateway to BRAiN. All external services 
          (Telegram, WhatsApp, Email) must connect through AXE, never directly to BRAiN.
        </p>
      </div>
    </div>
  );
}
