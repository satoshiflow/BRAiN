/**
 * React Query hooks for Telemetry Module
 *
 * Real-time robot telemetry monitoring with WebSocket support
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export interface TelemetryInfo {
  name: string;
  version: string;
  description: string;
  active_websockets: number;
  total_robots_monitored: number;
}

export interface RobotMetrics {
  robot_id: string;
  timestamp: string;
  cpu_usage?: number;
  memory_usage?: number;
  battery_level?: number;
  temperature?: number;
  position?: {
    x: number;
    y: number;
    z?: number;
  };
  velocity?: {
    x: number;
    y: number;
    z?: number;
  };
  status: string;
  custom_metrics?: Record<string, unknown>;
}

export interface TelemetryStats {
  total_robots: number;
  active_connections: number;
  messages_per_second: number;
  average_latency_ms: number;
  uptime_seconds: number;
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchTelemetryInfo(): Promise<TelemetryInfo> {
  const response = await fetch(`${API_BASE}/api/telemetry/info`);
  if (!response.ok) throw new Error(`Failed to fetch telemetry info: ${response.statusText}`);
  return response.json();
}

async function fetchRobotMetrics(robotId: string): Promise<RobotMetrics> {
  const response = await fetch(`${API_BASE}/api/telemetry/robots/${robotId}/metrics`);
  if (!response.ok) throw new Error(`Failed to fetch robot metrics: ${response.statusText}`);
  return response.json();
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get telemetry system information
 */
export function useTelemetryInfo() {
  return useQuery<TelemetryInfo>({
    queryKey: ['telemetry', 'info'],
    queryFn: fetchTelemetryInfo,
    staleTime: 300_000, // 5 minutes
    retry: 2,
  });
}

/**
 * Get robot metrics by ID
 */
export function useRobotMetrics(robotId: string | undefined) {
  return useQuery<RobotMetrics>({
    queryKey: ['telemetry', 'metrics', robotId],
    queryFn: () => fetchRobotMetrics(robotId!),
    enabled: !!robotId,
    refetchInterval: 5_000, // Refresh every 5 seconds
    staleTime: 3_000,
    retry: 2,
  });
}

/**
 * WebSocket hook for real-time metrics
 *
 * Usage:
 * ```tsx
 * const metrics = useTelemetryWebSocket('robot_001');
 * ```
 */
export function useTelemetryWebSocket(robotId: string | undefined) {
  const queryClient = useQueryClient();

  // This is a simplified version - full WebSocket integration would require more setup
  // For now, return the polled metrics
  return useRobotMetrics(robotId);
}

/**
 * Helper hook: Check if robot metrics are healthy
 */
export function useIsRobotHealthy(robotId: string | undefined) {
  const { data: metrics } = useRobotMetrics(robotId);

  if (!metrics) return null;

  const isHealthy =
    (metrics.battery_level ?? 100) > 20 &&
    (metrics.cpu_usage ?? 0) < 90 &&
    (metrics.temperature ?? 0) < 80 &&
    metrics.status !== 'error';

  return isHealthy;
}
