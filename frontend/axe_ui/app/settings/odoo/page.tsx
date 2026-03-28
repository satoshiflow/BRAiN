"use client";

import { useEffect, useState } from "react";
import { getApiBase } from "@/lib/config";

interface OdooSkill {
  skill_key: string;
  odoo_model: string;
  odoo_method: string;
  description: string;
  input_schema: Record<string, unknown>;
  risk_tier: string;
}

export default function OdooSettings() {
  const [skills, setSkills] = useState<OdooSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<OdooSkill | null>(null);
  const [payload, setPayload] = useState("");
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    try {
      const apiBase = getApiBase();
      const response = await fetch(`${apiBase}/api/odoo/skills`);
      
      if (!response.ok) {
        throw new Error("Failed to fetch Odoo skills");
      }
      
      const data = await response.json();
      setSkills(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const executeSkill = async () => {
    if (!selectedSkill) return;
    
    setExecuting(true);
    setResult(null);
    
    try {
      const apiBase = getApiBase();
      let parsedPayload = {};
      
      try {
        parsedPayload = payload ? JSON.parse(payload) : {};
      } catch {
        setResult("❌ Invalid JSON payload");
        setExecuting(false);
        return;
      }
      
      const response = await fetch(
        `${apiBase}/api/odoo/skills/${selectedSkill.skill_key}/execute`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsedPayload),
        }
      );
      
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setResult(`❌ Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setExecuting(false);
    }
  };

  const getRiskColor = (tier: string) => {
    switch (tier) {
      case "high":
        return "text-red-400 bg-red-500/20";
      case "medium":
        return "text-orange-400 bg-orange-500/20";
      case "low":
        return "text-green-400 bg-green-500/20";
      default:
        return "text-slate-400 bg-slate-500/20";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-cyan-400">📦 Loading Odoo Skills...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">📦 Odoo Skills</h1>
        <p className="text-slate-400">
          Verwalte und führe Odoo-Operationen aus
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">
          ❌ {error}
        </div>
      )}

      {/* Skills List */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-slate-400 border-b border-slate-800">
                <th className="p-4">Skill Key</th>
                <th className="p-4">Model</th>
                <th className="p-4">Method</th>
                <th className="p-4">Risk</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((skill) => (
                <tr
                  key={skill.skill_key}
                  onClick={() => setSelectedSkill(skill)}
                  className={`border-b border-slate-800/50 cursor-pointer transition-colors ${
                    selectedSkill?.skill_key === skill.skill_key
                      ? "bg-cyan-500/10"
                      : "hover:bg-slate-800/50"
                  }`}
                >
                  <td className="p-4">
                    <code className="text-sm text-cyan-400">{skill.skill_key}</code>
                  </td>
                  <td className="p-4 text-sm text-slate-300">{skill.odoo_model}</td>
                  <td className="p-4 text-sm text-slate-300">{skill.odoo_method}</td>
                  <td className="p-4">
                    <span className={`text-xs px-2 py-1 rounded ${getRiskColor(skill.risk_tier)}`}>
                      {skill.risk_tier}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Skill Executor */}
      {selectedSkill && (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-white">
                {selectedSkill.skill_key}
              </h2>
              <p className="text-sm text-slate-400">{selectedSkill.description}</p>
            </div>
            <button
              onClick={executeSkill}
              disabled={executing}
              className="px-4 py-2 bg-cyan-500 text-slate-900 rounded-lg font-medium hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {executing ? "⏳ Ausführen..." : "▶️ Ausführen"}
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Payload (JSON)
              </label>
              <textarea
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                placeholder='{"partner_id": 1, "lines": [...]}'
                className="w-full h-32 bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm text-slate-300 font-mono"
              />
            </div>

            {result && (
              <div>
                <label className="block text-sm text-slate-400 mb-2">Ergebnis</label>
                <pre className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm text-slate-300 overflow-x-auto max-h-64">
                  {result}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Help */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <h3 className="text-sm font-medium text-slate-400 mb-2">💡 Hinweis</h3>
        <p className="text-sm text-slate-500">
          Du kannst Odoo-Commands auch direkt im Chat verwenden:
        </p>
        <ul className="mt-2 text-sm text-slate-500 space-y-1">
          <li>• &quot;zeige mir die offenen Rechnungen&quot;</li>
          <li>• &quot;neuer Kunde: Max Mustermann&quot;</li>
          <li>• &quot;erstelle Auftrag für Kunde X&quot;</li>
        </ul>
      </div>
    </div>
  );
}
