/**
 * Learning from Demonstration API Client
 *
 * API client for learning from demonstration features:
 * - Demonstration recording
 * - Trajectory playback
 * - Policy learning
 */

import { fetchJson, API_BASE } from "./api"

// ========== Types ==========

export type DemonstrationMode = "teleoperation" | "kinesthetic" | "vision_based"

export interface TrajectoryPoint {
  timestamp: number
  position: Record<string, number>
  velocity: Record<string, number>
  orientation?: Record<string, number>
  gripper_state?: number
}

export interface Demonstration {
  demo_id: string
  robot_id: string
  task_name: string
  mode: DemonstrationMode
  trajectory: TrajectoryPoint[]
  duration_s: number
  success: boolean
  created_at?: number
}

export interface TrajectoryPlaybackRequest {
  demo_id: string
  robot_id: string
  speed_factor?: number
  loop?: boolean
}

export interface PolicyLearningRequest {
  policy_id: string
  task_name: string
  demonstration_ids: string[]
  algorithm: "behavioral_cloning" | "dagger" | "gail" | "irl"
  training_params?: Record<string, any>
}

export interface LearnedPolicy {
  policy_id: string
  task_name: string
  algorithm: string
  num_demonstrations: number
  training_accuracy: number
  validation_accuracy?: number
  generalization_score?: number
  model_path?: string
  created_at?: number
}

export interface LearningInfo {
  module: string
  version: string
  description: string
  features: string[]
  statistics: {
    total_demonstrations: number
    total_policies: number
    active_recordings: number
  }
}

export interface RecordingSession {
  demo_id: string
  robot_id: string
  task_name: string
  start_time: number
  point_count: number
}

// ========== API Functions ==========

/**
 * Get learning module info
 */
export async function fetchLearningInfo(): Promise<LearningInfo> {
  return fetchJson<LearningInfo>("/api/learning/info")
}

/**
 * Start demonstration recording
 */
export async function startRecording(
  demoId: string,
  robotId: string,
  taskName: string,
  mode: DemonstrationMode
): Promise<{ success: boolean; demo_id: string }> {
  const res = await fetch(`${API_BASE}/api/learning/demonstrations/start-recording`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      demo_id: demoId,
      robot_id: robotId,
      task_name: taskName,
      mode: mode,
    }),
  })

  if (!res.ok) {
    throw new Error(`Failed to start recording: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Add trajectory point to active recording
 */
export async function addTrajectoryPoint(
  demoId: string,
  point: TrajectoryPoint
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/learning/demonstrations/${demoId}/add-point`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(point),
  })

  if (!res.ok) {
    throw new Error(`Failed to add trajectory point: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Stop recording and save demonstration
 */
export async function stopRecording(
  demoId: string,
  mode: DemonstrationMode,
  success: boolean = true
): Promise<Demonstration> {
  const res = await fetch(`${API_BASE}/api/learning/demonstrations/stop-recording`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      demo_id: demoId,
      mode: mode,
      success: success,
    }),
  })

  if (!res.ok) {
    throw new Error(`Failed to stop recording: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get all demonstrations
 */
export async function fetchDemonstrations(): Promise<Demonstration[]> {
  return fetchJson<Demonstration[]>("/api/learning/demonstrations")
}

/**
 * Get demonstration by ID
 */
export async function fetchDemonstration(demoId: string): Promise<Demonstration> {
  return fetchJson<Demonstration>(`/api/learning/demonstrations/${demoId}`)
}

/**
 * Playback trajectory
 */
export async function playbackTrajectory(
  request: TrajectoryPlaybackRequest
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/learning/playback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.ok) {
    throw new Error(`Failed to playback trajectory: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Learn policy from demonstrations
 */
export async function learnPolicy(request: PolicyLearningRequest): Promise<LearnedPolicy> {
  const res = await fetch(`${API_BASE}/api/learning/policies/learn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.ok) {
    throw new Error(`Failed to learn policy: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get all learned policies
 */
export async function fetchPolicies(): Promise<LearnedPolicy[]> {
  return fetchJson<LearnedPolicy[]>("/api/learning/policies")
}

/**
 * Get learned policy by ID
 */
export async function fetchPolicy(policyId: string): Promise<LearnedPolicy> {
  return fetchJson<LearnedPolicy>(`/api/learning/policies/${policyId}`)
}

/**
 * Get active recording sessions
 */
export async function fetchActiveRecordings(): Promise<RecordingSession[]> {
  return fetchJson<RecordingSession[]>("/api/learning/recordings/active")
}
