import { apiRequest, fetchJson, createEventSource } from "./client";

export interface ModuleHealth {
  name: string;
  status: "up" | "down" | "degraded";
  lastCheck: string;
  responseTime?: number;
  errorRate?: number;
  metrics: Record<string, number>;
}

export interface HealthStatus {
  overall: "healthy" | "degraded" | "critical";
  uptime: number;
  version: string;
  timestamp: string;
  modules: ModuleHealth[];
}

export interface HealthMetrics {
  cpu: number;
  memory: number;
  requestsPerMinute: number;
  errorRate: number;
  avgResponseTime: number;
}

export interface HealthTrend {
  timestamp: string;
  cpu: number;
  memory: number;
  requestsPerMinute: number;
  errorRate: number;
}

export const healthApi = {
  getStatus: () => fetchJson<HealthStatus>("/api/health/status"),

  getModules: () => fetchJson<ModuleHealth[]>("/api/health/status"),

  getMetrics: () => fetchJson<HealthMetrics>("/api/health/metrics"),

  getTrends: (hours = 24) =>
    fetchJson<HealthTrend[]>(`/api/health/trends?hours=${hours}`),

  subscribe: () => createEventSource("/api/health/stream"),
};
