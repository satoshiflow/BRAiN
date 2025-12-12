"use client";

import { useState } from "react";
import Link from "next/link";

type LLMRawResponse = Record<string, any>;

interface LLMApiResponse {
  ok: boolean;
  model: string;
  prompt: string;
  raw_response: LLMRawResponse;
}

const BRAIN_BASE = (process.env.NEXT_PUBLIC_BRAIN_API_BASE_URL || "http://localhost:8000")
  .replace(/\/+$/, "");

const LLM_URL = `${BRAIN_BASE}/api/debug/llm-ping`;

export default function LlmDebugPage() {
  const [prompt, setPrompt] = useState<string>(
    "Sag kurz Hallo. Du bist BRAiN im Dev-Modus.",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LLMApiResponse | null>(null);

  async function runTest() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch(LLM_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ prompt }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
      }

      const data: LLMApiResponse = await resp.json();
      setResult(data);
    } catch (e: any) {
      console.error(e);
      setError(e?.message ?? "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }

  const niceResponse =
    result?.raw_response &&
    (result.raw_response.response ??
      result.raw_response.output ??
      JSON.stringify(result.raw_response, null, 2));

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#050816",
        color: "#e5e7eb",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        padding: "24px",
      }}
    >
      {/* Top-Bar */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>
            BRAiN – LLM Debug
          </h1>
          <p style={{ fontSize: "14px", color: "#9ca3af" }}>
            Testet die komplette Kette: Control Deck → Backend → Ollama → Modell.
          </p>
        </div>

        <nav style={{ display: "flex", gap: "8px" }}>
          <Link
            href="/brain/debug"
            style={{
              padding: "8px 12px",
              borderRadius: "999px",
              border: "1px solid #4b5563",
              fontSize: "13px",
              textDecoration: "none",
            }}
          >
            ← Zur BRAiN Debug Console
          </Link>
          <Link
            href="/"
            style={{
              padding: "8px 12px",
              borderRadius: "999px",
              border: "1px solid #4b5563",
              fontSize: "13px",
              textDecoration: "none",
            }}
          >
            ⌂ Control Deck Home
          </Link>
        </nav>
      </header>

      <main
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1fr)",
          gap: "20px",
        }}
      >
        {/* Prompt & Status */}
        <section
          style={{
            background: "rgba(15,23,42,0.9)",
            borderRadius: "16px",
            padding: "18px",
            border: "1px solid #1f2937",
          }}
        >
          <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "8px" }}>
            Prompt
          </h2>
          <p style={{ fontSize: "12px", color: "#9ca3af", marginBottom: "8px" }}>
            Dieser Test spricht den Endpoint{" "}
            <code style={{ fontFamily: "monospace" }}>/api/debug/llm-ping</code> an.
          </p>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={6}
            style={{
              width: "100%",
              resize: "vertical",
              background: "#020617",
              color: "#e5e7eb",
              borderRadius: "12px",
              border: "1px solid #374151",
              padding: "10px",
              fontSize: "14px",
              fontFamily: "monospace",
              marginBottom: "12px",
            }}
          />

          <button
            onClick={runTest}
            disabled={loading}
            style={{
              padding: "8px 16px",
              borderRadius: "999px",
              border: "none",
              cursor: loading ? "default" : "pointer",
              fontSize: "14px",
              fontWeight: 500,
              background: loading ? "#4b5563" : "#22c55e",
              color: "#020617",
              marginBottom: "10px",
            }}
          >
            {loading ? "LLM wird abgefragt ..." : "LLM-Test starten"}
          </button>

          {/* Status / Fehler */}
          {error && (
            <div
              style={{
                marginTop: "8px",
                padding: "8px 10px",
                borderRadius: "8px",
                border: "1px solid #b91c1c",
                background: "rgba(185,28,28,0.1)",
                fontSize: "13px",
              }}
            >
              <strong>Fehler:</strong> {error}
            </div>
          )}

          {result && !error && (
            <div style={{ marginTop: "10px", fontSize: "13px" }}>
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "3px 8px",
                    borderRadius: "999px",
                    border: "1px solid #22c55e",
                    fontSize: "11px",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "999px",
                      background: result.ok ? "#22c55e" : "#f97316",
                    }}
                  />
                  {result.ok ? "OK" : "Fehler"}
                </span>
                <span style={{ fontSize: "12px", color: "#9ca3af" }}>
                  Modell: <code>{result.model}</code>
                </span>
              </div>
            </div>
          )}
        </section>

        {/* Ausgabe */}
        <section
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div
            style={{
              background: "rgba(15,23,42,0.9)",
              borderRadius: "16px",
              padding: "16px",
              border: "1px solid #1f2937",
              minHeight: "140px",
            }}
          >
            <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "8px" }}>
              LLM Antwort
            </h2>
            {!result && !error && (
              <p style={{ fontSize: "13px", color: "#9ca3af" }}>
                Starte einen Test, um hier die Antwort von <code>phi3</code> zu sehen.
              </p>
            )}
            {niceResponse && (
              <p
                style={{
                  whiteSpace: "pre-wrap",
                  fontSize: "14px",
                  lineHeight: 1.5,
                }}
              >
                {niceResponse}
              </p>
            )}
          </div>

          <div
            style={{
              background: "rgba(15,23,42,0.9)",
              borderRadius: "16px",
              padding: "16px",
              border: "1px solid #111827",
              maxHeight: "260px",
              overflow: "auto",
              fontSize: "12px",
            }}
          >
            <h3 style={{ fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              Rohdaten (Debug)
            </h3>
            {result ? (
              <pre
                style={{
                  whiteSpace: "pre",
                  fontFamily: "monospace",
                }}
              >
                {JSON.stringify(result.raw_response, null, 2)}
              </pre>
            ) : (
              <p style={{ color: "#6b7280" }}>Noch keine Daten.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}