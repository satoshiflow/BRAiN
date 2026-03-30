import { fetchJson, postJson, putJson } from "./client";

export interface BrainParameter {
  key: string;
  value: number;
  min: number;
  max: number;
  description: string;
}

export interface BrainState {
  name: string;
  description: string;
  parameters: Record<string, number>;
  isDefault?: boolean;
}

export interface NeuralExecution {
  id: string;
  action: string;
  timestamp: string;
  parameters: Record<string, number>;
  result?: string;
  duration?: number;
  success: boolean;
}

export interface NeuralStats {
  totalExecutions: number;
  avgDuration: number;
  successRate: number;
}

export const neuralApi = {
  getParameters: () => fetchJson<BrainParameter[]>("/api/neural/parameters"),

  getParameter: (key: string) =>
    fetchJson<BrainParameter>(`/api/neural/parameters/${key}`),

  updateParameter: (key: string, value: number) =>
    putJson<{ success: boolean }, { value: number }>(
      `/api/neural/parameters/${key}`,
      { value }
    ),

  getStates: () => fetchJson<BrainState[]>("/api/neural/states"),

  getState: (stateName: string) =>
    fetchJson<BrainState>(`/api/neural/states/${stateName}`),

  applyState: (stateName: string) =>
    postJson<{ success: boolean }, unknown>("/api/neural/states", {
      name: stateName,
    }),

  execute: (action: string, payload: Record<string, unknown> = {}) =>
    postJson<NeuralExecution, { action: string; payload: Record<string, unknown> }>(
      "/api/neural/execute",
      { action, payload }
    ),

  getExecutions: (limit = 20) =>
    fetchJson<NeuralExecution[]>(`/api/neural/executions?limit=${limit}`),

  getStats: () => fetchJson<NeuralStats>("/api/neural/stats"),
};
