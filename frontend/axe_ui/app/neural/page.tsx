"use client";

import { useEffect, useState } from "react";
import { getApiBase } from "@/lib/config";

interface NeuralParameter {
  key: string;
  value: number;
  min_value: number;
  max_value: number;
  description: string;
}

interface NeuralState {
  state_name: string;
  creativity: number;
  caution: number;
  speed: number;
  is_active: boolean;
}

interface NeuralSynapse {
  synapse_id: string;
  target: string;
  capability: string;
  weight: number;
  bias: number;
  is_active: boolean;
}

interface NeuralStats {
  total_executions: number;
  avg_execution_time_ms: number;
  cache_hit_rate: number;
}

export default function NeuralDashboard() {
  const [parameters, setParameters] = useState<NeuralParameter[]>([]);
  const [states, setStates] = useState<NeuralState[]>([]);
  const [synapses, setSynapses] = useState<NeuralSynapse[]>([]);
  const [stats, setStats] = useState<NeuralStats | null>(null);
  const [activeState, setActiveState] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNeuralData();
  }, []);

  const fetchNeuralData = async () => {
    try {
      const apiBase = getApiBase();
      
      const [paramsRes, statesRes, synapsesRes, statsRes] = await Promise.all([
        fetch(`${apiBase}/api/neural/parameters`),
        fetch(`${apiBase}/api/neural/states`),
        fetch(`${apiBase}/api/neural/synapses`),
        fetch(`${apiBase}/api/neural/stats`),
      ]);

      if (!paramsRes.ok || !statesRes.ok || !synapsesRes.ok) {
        throw new Error("Failed to fetch neural data");
      }

      const paramsData = await paramsRes.json();
      const statesData = await statesRes.json();
      const synapsesData = await synapsesRes.json();
      const statsData = await statsRes.json();

      setParameters(paramsData.parameters || []);
      setStates(statesData.states || []);
      setSynapses(synapsesData.synapses || []);
      setStats(statsData);

      // Find active state
      const active = (statesData.states || []).find((s: NeuralState) => s.is_active);
      if (active) {
        setActiveState(active.state_name);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const switchState = async (stateName: string) => {
    try {
      const apiBase = getApiBase();
      const response = await fetch(`${apiBase}/api/neural/states`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state_name: stateName }),
      });

      if (response.ok) {
        setActiveState(stateName);
        fetchNeuralData();
      }
    } catch (err) {
      console.error("Failed to switch state:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-cyan-400">🧠 Loading Neural Core...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-400">❌ Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">🧠 Neural Core Dashboard</h1>
          <p className="text-slate-400">Brain 3.0 Parameter und Synapsen</p>
        </div>
        <div className="text-sm text-slate-500">
          {stats && (
            <span>{stats.total_executions} executions • {stats.cache_hit_rate}% cache</span>
          )}
        </div>
      </div>

      {/* State Switcher */}
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
        <h2 className="text-sm font-medium text-slate-400 mb-3">Aktiver State</h2>
        <div className="flex gap-2">
          {states.map((state) => (
            <button
              key={state.state_name}
              onClick={() => switchState(state.state_name)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                activeState === state.state_name
                  ? "bg-cyan-500 text-slate-900"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {state.state_name}
            </button>
          ))}
        </div>
      </div>

      {/* Parameters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {parameters.map((param) => (
          <div
            key={param.key}
            className="bg-slate-900 rounded-xl p-4 border border-slate-800"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-300">{param.key}</span>
              <span className="text-lg font-bold text-cyan-400">
                {param.value.toFixed(2)}
              </span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2">
              <div
                className="bg-cyan-500 h-2 rounded-full transition-all"
                style={{ width: `${((param.value - param.min_value) / (param.max_value - param.min_value)) * 100}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">{param.description}</p>
          </div>
        ))}
      </div>

      {/* Synapses */}
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
        <h2 className="text-lg font-semibold text-white mb-4">Synapsen</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-slate-400 border-b border-slate-800">
                <th className="pb-2">ID</th>
                <th className="pb-2">Target</th>
                <th className="pb-2">Capability</th>
                <th className="pb-2">Weight</th>
                <th className="pb-2">Bias</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {synapses.map((synapse) => (
                <tr key={synapse.synapse_id} className="border-b border-slate-800/50">
                  <td className="py-2 text-sm font-mono text-slate-300">
                    {synapse.synapse_id.slice(0, 8)}...
                  </td>
                  <td className="py-2 text-sm text-slate-300">{synapse.target}</td>
                  <td className="py-2 text-sm text-slate-300">{synapse.capability}</td>
                  <td className="py-2 text-sm text-cyan-400">{synapse.weight.toFixed(2)}</td>
                  <td className="py-2 text-sm text-orange-400">{synapse.bias.toFixed(2)}</td>
                  <td className="py-2">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        synapse.is_active
                          ? "bg-green-500/20 text-green-400"
                          : "bg-slate-700 text-slate-400"
                      }`}
                    >
                      {synapse.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
