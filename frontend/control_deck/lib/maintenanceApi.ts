/**
 * Predictive Maintenance API Client
 *
 * API client for predictive maintenance features:
 * - Health monitoring
 * - Anomaly detection
 * - Failure prediction
 * - Maintenance scheduling
 */

import { fetchJson, API_BASE } from "./api"

// ========== Types ==========

export type ComponentType = "motor" | "battery" | "sensor" | "actuator" | "controller" | "drive_system" | "manipulator" | "communication"
export type AnomalyType = "temperature_spike" | "vibration_anomaly" | "power_fluctuation" | "performance_degradation" | "sensor_drift" | "communication_loss" | "unexpected_behavior"
export type AnomalySeverity = "low" | "medium" | "high" | "critical"
export type MaintenanceType = "inspection" | "lubrication" | "calibration" | "component_replacement" | "software_update" | "cleaning" | "preventive" | "corrective"
export type MaintenanceStatus = "scheduled" | "in_progress" | "completed" | "cancelled" | "overdue"

export interface HealthMetrics {
  component_id: string
  component_type: ComponentType
  robot_id: string
  timestamp: number
  health_score: number
  temperature_c?: number
  vibration_level?: number
  power_consumption_w?: number
  operating_hours?: number
  cycle_count?: number
  error_rate?: number
  response_time_ms?: number
  custom_metrics?: Record<string, number>
}

export interface AnomalyDetection {
  anomaly_id: string
  robot_id: string
  component_id: string
  component_type: ComponentType
  anomaly_type: AnomalyType
  severity: AnomalySeverity
  detected_at: number
  anomaly_score: number
  baseline_value?: number
  current_value?: number
  deviation_percentage?: number
  description: string
  recommended_action?: string
  acknowledged: boolean
}

export interface FailurePrediction {
  prediction_id: string
  robot_id: string
  component_id: string
  component_type: ComponentType
  failure_probability: number
  predicted_failure_time?: number
  time_to_failure_hours?: number
  confidence_score: number
  root_cause?: string
  contributing_factors: string[]
  recommended_actions: string[]
  estimated_downtime_hours?: number
}

export interface MaintenanceSchedule {
  schedule_id: string
  robot_id: string
  component_id?: string
  component_type?: ComponentType
  maintenance_type: MaintenanceType
  status: MaintenanceStatus
  scheduled_time: number
  estimated_duration_hours: number
  description: string
  priority: number
  required_parts: string[]
  required_tools: string[]
  technician_notes?: string
  completed_at?: number
  actual_duration_hours?: number
  completion_notes?: string
}

export interface ComponentHealthSummary {
  component_type: ComponentType
  total_components: number
  healthy_components: number
  degraded_components: number
  critical_components: number
  average_health_score: number
  average_operating_hours?: number
}

export interface MaintenanceAnalytics {
  total_robots: number
  total_components: number
  health_summaries: ComponentHealthSummary[]
  active_anomalies: number
  pending_predictions: number
  scheduled_maintenance_count: number
  overdue_maintenance_count: number
  average_fleet_health: number
  uptime_percentage: number
}

export interface MaintenanceInfo {
  module: string
  version: string
  description: string
  features: string[]
  statistics: {
    total_components_monitored: number
    active_anomalies: number
    pending_predictions: number
    scheduled_tasks: number
  }
}

// ========== API Functions ==========

/**
 * Get maintenance module info
 */
export async function fetchMaintenanceInfo(): Promise<MaintenanceInfo> {
  return fetchJson<MaintenanceInfo>("/api/maintenance/info")
}

/**
 * Record health metrics
 */
export async function recordHealthMetrics(metrics: HealthMetrics): Promise<HealthMetrics> {
  const res = await fetch(`${API_BASE}/api/maintenance/health-metrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metrics),
  })

  if (!res.ok) {
    throw new Error(`Failed to record health metrics: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get health metrics history
 */
export async function fetchHealthMetrics(params?: {
  component_id?: string
  robot_id?: string
  limit?: number
}): Promise<HealthMetrics[]> {
  const query = new URLSearchParams()
  if (params?.component_id) query.set("component_id", params.component_id)
  if (params?.robot_id) query.set("robot_id", params.robot_id)
  if (params?.limit) query.set("limit", params.limit.toString())

  const url = `/api/maintenance/health-metrics${query.toString() ? `?${query}` : ""}`
  return fetchJson<HealthMetrics[]>(url)
}

/**
 * Get detected anomalies
 */
export async function fetchAnomalies(params?: {
  robot_id?: string
  severity?: AnomalySeverity
  acknowledged?: boolean
}): Promise<AnomalyDetection[]> {
  const query = new URLSearchParams()
  if (params?.robot_id) query.set("robot_id", params.robot_id)
  if (params?.severity) query.set("severity", params.severity)
  if (params?.acknowledged !== undefined) query.set("acknowledged", params.acknowledged.toString())

  const url = `/api/maintenance/anomalies${query.toString() ? `?${query}` : ""}`
  return fetchJson<AnomalyDetection[]>(url)
}

/**
 * Acknowledge anomaly
 */
export async function acknowledgeAnomaly(anomalyId: string): Promise<AnomalyDetection> {
  const res = await fetch(`${API_BASE}/api/maintenance/anomalies/${anomalyId}/acknowledge`, {
    method: "POST",
  })

  if (!res.ok) {
    throw new Error(`Failed to acknowledge anomaly: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Predict component failure
 */
export async function predictFailure(componentId: string): Promise<FailurePrediction | null> {
  const res = await fetch(`${API_BASE}/api/maintenance/predictions/${componentId}`, {
    method: "POST",
  })

  if (!res.ok) {
    throw new Error(`Failed to predict failure: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get failure predictions
 */
export async function fetchPredictions(params?: {
  robot_id?: string
  min_probability?: number
}): Promise<FailurePrediction[]> {
  const query = new URLSearchParams()
  if (params?.robot_id) query.set("robot_id", params.robot_id)
  if (params?.min_probability !== undefined) query.set("min_probability", params.min_probability.toString())

  const url = `/api/maintenance/predictions${query.toString() ? `?${query}` : ""}`
  return fetchJson<FailurePrediction[]>(url)
}

/**
 * Schedule maintenance
 */
export async function scheduleMaintenance(schedule: MaintenanceSchedule): Promise<MaintenanceSchedule> {
  const res = await fetch(`${API_BASE}/api/maintenance/schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(schedule),
  })

  if (!res.ok) {
    throw new Error(`Failed to schedule maintenance: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get maintenance schedules
 */
export async function fetchMaintenanceSchedules(params?: {
  robot_id?: string
  status?: MaintenanceStatus
}): Promise<MaintenanceSchedule[]> {
  const query = new URLSearchParams()
  if (params?.robot_id) query.set("robot_id", params.robot_id)
  if (params?.status) query.set("status", params.status)

  const url = `/api/maintenance/schedules${query.toString() ? `?${query}` : ""}`
  return fetchJson<MaintenanceSchedule[]>(url)
}

/**
 * Update maintenance status
 */
export async function updateMaintenanceStatus(
  scheduleId: string,
  status: MaintenanceStatus,
  completionNotes?: string
): Promise<MaintenanceSchedule> {
  const res = await fetch(`${API_BASE}/api/maintenance/schedules/${scheduleId}/status`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status: status,
      completion_notes: completionNotes,
    }),
  })

  if (!res.ok) {
    throw new Error(`Failed to update maintenance status: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get maintenance analytics
 */
export async function fetchMaintenanceAnalytics(params?: {
  robot_ids?: string[]
  component_types?: ComponentType[]
}): Promise<MaintenanceAnalytics> {
  const query = new URLSearchParams()
  if (params?.robot_ids) {
    params.robot_ids.forEach(id => query.append("robot_ids", id))
  }
  if (params?.component_types) {
    params.component_types.forEach(type => query.append("component_types", type))
  }

  const url = `/api/maintenance/analytics${query.toString() ? `?${query}` : ""}`
  return fetchJson<MaintenanceAnalytics>(url)
}
