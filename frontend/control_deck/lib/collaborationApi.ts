/**
 * Collaboration API Client
 *
 * API client for multi-robot collaboration features:
 * - Formation control
 * - Task allocation
 * - Shared world models
 */

import { fetchJson, API_BASE } from "./api"

// ========== Types ==========

export type FormationType = "line" | "column" | "wedge" | "circle" | "grid" | "custom"
export type TaskAllocationStrategy = "greedy" | "auction" | "consensus" | "learning_based"
export type CoordinationMode = "leader_follower" | "distributed" | "centralized"

export interface FormationConfig {
  formation_id: string
  formation_type: FormationType
  robot_ids: string[]
  leader_id: string
  inter_robot_distance: number
  behavior: "tight" | "loose" | "adaptive"
  formation_params?: Record<string, any>
}

export interface CollaborativeTask {
  task_id: string
  task_type: string
  description: string
  required_robots: number
  assigned_robots: string[]
  allocation_strategy: TaskAllocationStrategy
  coordination_mode: CoordinationMode
  priority: number
  status: "pending" | "allocated" | "executing" | "completed" | "failed"
  created_at?: number
}

export interface TaskBid {
  task_id: string
  robot_id: string
  bid_value: number
  estimated_time: number
  estimated_cost: number
  capabilities: string[]
}

export interface SharedWorldModel {
  model_id: string
  robot_ids: string[]
  map_data?: any
  obstacles?: any[]
  landmarks?: any[]
  last_updated: number
  consensus_level: number
}

export interface CollaborationInfo {
  module: string
  version: string
  description: string
  features: string[]
  statistics: {
    active_formations: number
    pending_tasks: number
    allocated_tasks: number
    world_models: number
  }
}

// ========== API Functions ==========

/**
 * Get collaboration module info
 */
export async function fetchCollaborationInfo(): Promise<CollaborationInfo> {
  return fetchJson<CollaborationInfo>("/api/collaboration/info")
}

/**
 * Get all formations
 */
export async function fetchFormations(): Promise<FormationConfig[]> {
  return fetchJson<FormationConfig[]>("/api/collaboration/formations")
}

/**
 * Get formation by ID
 */
export async function fetchFormation(formationId: string): Promise<FormationConfig> {
  return fetchJson<FormationConfig>(`/api/collaboration/formations/${formationId}`)
}

/**
 * Create new formation
 */
export async function createFormation(config: FormationConfig): Promise<FormationConfig> {
  const res = await fetch(`${API_BASE}/api/collaboration/formations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })

  if (!res.ok) {
    throw new Error(`Failed to create formation: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Update formation
 */
export async function updateFormation(
  formationId: string,
  config: Partial<FormationConfig>
): Promise<FormationConfig> {
  const res = await fetch(`${API_BASE}/api/collaboration/formations/${formationId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })

  if (!res.ok) {
    throw new Error(`Failed to update formation: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get all collaborative tasks
 */
export async function fetchTasks(): Promise<CollaborativeTask[]> {
  return fetchJson<CollaborativeTask[]>("/api/collaboration/tasks")
}

/**
 * Create collaborative task
 */
export async function createTask(task: Omit<CollaborativeTask, "task_id" | "assigned_robots" | "status">): Promise<CollaborativeTask> {
  const res = await fetch(`${API_BASE}/api/collaboration/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(task),
  })

  if (!res.ok) {
    throw new Error(`Failed to create task: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Submit task bid
 */
export async function submitBid(bid: TaskBid): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/collaboration/tasks/${bid.task_id}/bids`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bid),
  })

  if (!res.ok) {
    throw new Error(`Failed to submit bid: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Allocate task (auction-based)
 */
export async function allocateTask(taskId: string): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/collaboration/tasks/${taskId}/allocate`, {
    method: "POST",
  })

  if (!res.ok) {
    throw new Error(`Failed to allocate task: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get shared world models
 */
export async function fetchWorldModels(): Promise<SharedWorldModel[]> {
  return fetchJson<SharedWorldModel[]>("/api/collaboration/world-models")
}

/**
 * Create shared world model
 */
export async function createWorldModel(model: Omit<SharedWorldModel, "model_id">): Promise<SharedWorldModel> {
  const res = await fetch(`${API_BASE}/api/collaboration/world-models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(model),
  })

  if (!res.ok) {
    throw new Error(`Failed to create world model: ${res.statusText}`)
  }

  return res.json()
}
