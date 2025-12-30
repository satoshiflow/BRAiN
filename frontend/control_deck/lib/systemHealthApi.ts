/**
 * System Health API Client
 *
 * Type-safe API client for comprehensive system health monitoring.
 */

import { fetchJson } from "./api";

// =============================================================================
// TYPES
// =============================================================================

export type HealthStatus = "healthy" | "degraded" | "critical" | "unknown";

export type BottleneckSeverity = "low" | "medium" | "high" | "critical";

export interface BottleneckInfo {
  component: string;
  location: string;
  severity: BottleneckSeverity;
  metric_value?: number;
  metric_unit?: string;
  description: string;
  recommendation: string;
}

export interface OptimizationRecommendation {
  priority: string;
  category: string;
  title: string;
  description: string;
  impact?: string;
  effort?: string;
}

export interface ImmuneHealthData {
  active_issues: number;
  critical_issues: number;
  last_event_timestamp?: number;
  event_rate_per_minute?: number;
}

export interface ThreatsHealthData {
  total_threats: number;
  active_threats: number;
  critical_threats: number;
  mitigated_threats: number;
  last_threat_timestamp?: number;
}

export interface MissionHealthData {
  queue_depth: number;
  running_missions: number;
  pending_missions: number;
  completed_today: number;
  failed_today: number;
  avg_latency_ms?: number;
  throughput_per_second?: number;
}

export interface AgentHealthData {
  total_agents: number;
  active_agents: number;
  idle_agents: number;
  avg_utilization?: number;
}

export interface AuditMetrics {
  edge_of_chaos_score?: number;
  memory_leak_detected: boolean;
  deadlock_detected: boolean;
  starvation_detected: boolean;
  cascade_failure_detected: boolean;
  avg_latency_ms?: number;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
  throughput_per_second?: number;
  memory_usage_mb?: number;
  memory_trend?: string;
  cpu_usage_percent?: number;
}

export interface SystemHealth {
  overall_status: HealthStatus;
  timestamp: string;
  uptime_seconds?: number;
  immune_health?: ImmuneHealthData;
  threats_health?: ThreatsHealthData;
  mission_health?: MissionHealthData;
  agent_health?: AgentHealthData;
  audit_metrics?: AuditMetrics;
  bottlenecks: BottleneckInfo[];
  recommendations: OptimizationRecommendation[];
  metadata: Record<string, any>;
}

export interface SystemHealthSummary {
  status: HealthStatus;
  timestamp: string;
  critical_issues_count: number;
  edge_of_chaos_score?: number;
  message?: string;
}

// =============================================================================
// RUNTIME AUDITOR TYPES
// =============================================================================

export interface PerformanceMetrics {
  avg_latency_ms?: number;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
  throughput_per_second?: number;
  samples_count: number;
}

export interface ResourceMetrics {
  memory_usage_mb?: number;
  memory_trend?: string;
  memory_growth_rate_mb_per_min?: number;
  cpu_usage_percent?: number;
  disk_usage_percent?: number;
}

export interface QueueMetrics {
  queue_depth: number;
  queue_depth_trend?: string;
  avg_queue_depth?: number;
  max_queue_depth: number;
}

export interface EdgeOfChaosMetrics {
  score?: number;
  entropy?: number;
  synchronicity_index?: number;
  agent_utilization_variance?: number;
  assessment?: string;
}

export interface AnomalyDetection {
  type: string;
  severity: string;
  detected_at: string;
  description: string;
  metric_value?: number;
  threshold?: number;
  recommendation?: string;
}

export interface RuntimeMetrics {
  timestamp: string;
  uptime_seconds: number;
  performance: PerformanceMetrics;
  resources: ResourceMetrics;
  queue: QueueMetrics;
  edge_of_chaos: EdgeOfChaosMetrics;
  anomalies: AnomalyDetection[];
  memory_leak_detected: boolean;
  deadlock_detected: boolean;
  starvation_detected: boolean;
  cascade_failure_detected: boolean;
  metadata: Record<string, any>;
}

export interface RuntimeAuditorStatus {
  running: boolean;
  last_collection_timestamp?: string;
  collection_interval_seconds: number;
  samples_collected: number;
  anomalies_detected: number;
}

// =============================================================================
// IMMUNE SYSTEM SELF-PROTECTION TYPES
// =============================================================================

export interface ProtectionStatus {
  backpressure_enabled: boolean;
  circuit_breaker_open: boolean;
  protection_actions_count: number;
  last_action?: {
    timestamp: string;
    event_id: number;
    event_type: string;
    action?: string;
    success: boolean;
    error?: string;
  };
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Get comprehensive system health
 */
export async function fetchSystemHealth(): Promise<SystemHealth> {
  return fetchJson<SystemHealth>("/api/system/health");
}

/**
 * Get lightweight health summary
 */
export async function fetchSystemHealthSummary(): Promise<SystemHealthSummary> {
  return fetchJson<SystemHealthSummary>("/api/system/health/summary");
}

/**
 * Get simple health status
 */
export async function fetchHealthStatus(): Promise<{
  status: string;
  timestamp: string;
  ok: boolean;
}> {
  return fetchJson("/api/system/health/status");
}

/**
 * Get runtime audit metrics
 */
export async function fetchRuntimeMetrics(): Promise<RuntimeMetrics> {
  return fetchJson<RuntimeMetrics>("/api/audit/runtime/metrics");
}

/**
 * Get runtime auditor status
 */
export async function fetchRuntimeAuditorStatus(): Promise<RuntimeAuditorStatus> {
  return fetchJson<RuntimeAuditorStatus>("/api/audit/runtime/status");
}

/**
 * Start runtime auditor background collection
 */
export async function startRuntimeAuditor(): Promise<{ message: string; running: boolean }> {
  return fetchJson("/api/audit/runtime/start", { method: "POST" });
}

/**
 * Stop runtime auditor background collection
 */
export async function stopRuntimeAuditor(): Promise<{ message: string; running: boolean }> {
  return fetchJson("/api/audit/runtime/stop", { method: "POST" });
}

/**
 * Get immune system self-protection status
 */
export async function fetchProtectionStatus(): Promise<ProtectionStatus> {
  return fetchJson<ProtectionStatus>("/api/immune/protection/status");
}

/**
 * Disable backpressure
 */
export async function disableBackpressure(): Promise<{ message: string; status: ProtectionStatus }> {
  return fetchJson("/api/immune/protection/backpressure/disable", { method: "POST" });
}

/**
 * Close circuit breaker
 */
export async function closeCircuitBreaker(): Promise<{ message: string; status: ProtectionStatus }> {
  return fetchJson("/api/immune/protection/circuit-breaker/close", { method: "POST" });
}
