import { fetchJson, createEventSource } from "./client";

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

interface BackendHealthService {
  service_name: string;
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  last_check_at?: string | null;
  response_time_ms?: number | null;
  total_checks: number;
  failed_checks: number;
}

interface BackendHealthStatus {
  overall_status: "healthy" | "degraded" | "unhealthy" | "unknown";
  checked_at: string;
  services: BackendHealthService[];
}

function mapOverallStatus(status: BackendHealthStatus["overall_status"]): HealthStatus["overall"] {
  if (status === "healthy") {
    return "healthy";
  }

  if (status === "degraded") {
    return "degraded";
  }

  return "critical";
}

function mapModuleStatus(status: BackendHealthService["status"]): ModuleHealth["status"] {
  if (status === "healthy") {
    return "up";
  }

  if (status === "degraded") {
    return "degraded";
  }

  return "down";
}

function mapHealthStatus(payload: BackendHealthStatus): HealthStatus {
  const modules: ModuleHealth[] = payload.services.map((service) => ({
    name: service.service_name,
    status: mapModuleStatus(service.status),
    lastCheck: service.last_check_at || payload.checked_at,
    responseTime: service.response_time_ms ?? undefined,
    errorRate:
      service.total_checks > 0
        ? Number(((service.failed_checks / service.total_checks) * 100).toFixed(1))
        : undefined,
    metrics: {},
  }));

  return {
    overall: mapOverallStatus(payload.overall_status),
    uptime: 0,
    version: "local",
    timestamp: payload.checked_at,
    modules,
  };
}

export const healthApi = {
  getStatus: async () => {
    const payload = await fetchJson<BackendHealthStatus>("/api/health/status");
    return mapHealthStatus(payload);
  },

  getModules: async () => {
    const payload = await fetchJson<BackendHealthStatus>("/api/health/status");
    return mapHealthStatus(payload).modules;
  },

  getMetrics: () => fetchJson<HealthMetrics>("/api/health/metrics"),

  getTrends: (hours = 24) =>
    fetchJson<HealthTrend[]>(`/api/health/trends?hours=${hours}`),

  subscribe: () => createEventSource("/api/health/stream"),

  mapStreamPayload: (payload: BackendHealthStatus) => mapHealthStatus(payload),
};
