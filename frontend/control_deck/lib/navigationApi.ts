/**
 * Advanced Navigation API Client
 *
 * API client for social-aware navigation features:
 * - Path planning
 * - Dynamic obstacle avoidance
 * - Formation navigation
 * - Context adaptation
 */

import { fetchJson, API_BASE } from "./api"

// ========== Types ==========

export type NavigationContext = "hospital" | "warehouse" | "office" | "street" | "mall" | "factory" | "home" | "outdoor"
export type SocialZone = "intimate" | "personal" | "social" | "public"
export type ObstacleType = "static" | "dynamic" | "human" | "robot" | "vehicle" | "unknown"
export type PathPlanningMode = "direct" | "social_aware" | "formation" | "dynamic_window" | "elastic_band" | "rrt_star"
export type NavigationBehavior = "assertive" | "cautious" | "social" | "balanced"
export type ObstacleAvoidanceStrategy = "stop_and_wait" | "replan" | "local_deform" | "social_force"

export interface Position2D {
  x: number
  y: number
  theta?: number
}

export interface Velocity2D {
  linear: number
  angular: number
}

export interface Obstacle {
  obstacle_id: string
  obstacle_type: ObstacleType
  position: Position2D
  velocity?: Velocity2D
  radius: number
  uncertainty?: number
  is_stationary?: boolean
  predicted_path?: Position2D[]
  social_zone?: SocialZone
}

export interface NavigationGoal {
  goal_id: string
  robot_id: string
  target_position: Position2D
  max_velocity?: number
  max_angular_velocity?: number
  goal_tolerance?: number
  angle_tolerance?: number
  navigation_context?: NavigationContext
  behavior?: NavigationBehavior
  planning_mode?: PathPlanningMode
  min_human_distance?: number
  min_robot_distance?: number
}

export interface PathSegment {
  position: Position2D
  velocity: Velocity2D
  timestamp: number
  curvature?: number
}

export interface PlannedPath {
  path_id: string
  goal_id: string
  robot_id: string
  segments: PathSegment[]
  total_distance: number
  estimated_duration: number
  social_cost?: number
  safety_score: number
}

export interface NavigationStatus {
  robot_id: string
  goal_id?: string
  is_navigating: boolean
  current_position: Position2D
  current_velocity: Velocity2D
  distance_to_goal?: number
  eta_seconds?: number
  obstacles_detected: number
  replanning_count: number
  last_update: number
}

export interface SocialNavigationParams {
  intimate_zone_radius: number
  personal_zone_radius: number
  social_zone_radius: number
  efficiency_weight: number
  safety_weight: number
  comfort_weight: number
  approach_angle_deg: number
  passing_side_preference: string
  max_crowd_density: number
  crowd_avoidance_margin: number
}

export interface FormationNavigationRequest {
  formation_id: string
  robot_ids: string[]
  leader_id: string
  target_position: Position2D
  formation_type: string
  inter_robot_distance: number
  maintain_orientation?: boolean
}

export interface DynamicObstacleAvoidanceRequest {
  robot_id: string
  current_position: Position2D
  current_velocity: Velocity2D
  goal_position: Position2D
  detected_obstacles: Obstacle[]
  avoidance_strategy?: ObstacleAvoidanceStrategy
  prediction_horizon_s?: number
}

export interface AvoidanceManeuver {
  maneuver_id: string
  robot_id: string
  recommended_velocity: Velocity2D
  duration_s: number
  safety_margin: number
  collision_risk: number
  maneuver_type: string
}

export interface ContextAdaptationRequest {
  robot_id: string
  navigation_context: NavigationContext
  detected_humans?: number
  crowd_density?: number
  noise_level_db?: number
  lighting_level_lux?: number
}

export interface AdaptedNavigationParams {
  context: NavigationContext
  max_velocity: number
  max_acceleration: number
  social_distance: number
  behavior: NavigationBehavior
  adaptations_applied: string[]
  reasoning: string
}

export interface NavigationInfo {
  module: string
  version: string
  description: string
  features: string[]
  planning_modes: string[]
  avoidance_strategies: string[]
  supported_contexts: string[]
  statistics: {
    active_goals: number
    planned_paths: number
    tracked_robots: number
    total_obstacles: number
  }
}

// ========== API Functions ==========

/**
 * Get navigation module info
 */
export async function fetchNavigationInfo(): Promise<NavigationInfo> {
  return fetchJson<NavigationInfo>("/api/navigation/info")
}

/**
 * Plan path to goal
 */
export async function planPath(goal: NavigationGoal): Promise<PlannedPath> {
  const res = await fetch(`${API_BASE}/api/navigation/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(goal),
  })

  if (!res.ok) {
    throw new Error(`Failed to plan path: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get planned path by ID
 */
export async function fetchPath(pathId: string): Promise<PlannedPath> {
  return fetchJson<PlannedPath>(`/api/navigation/paths/${pathId}`)
}

/**
 * Get navigation goal by ID
 */
export async function fetchGoal(goalId: string): Promise<NavigationGoal> {
  return fetchJson<NavigationGoal>(`/api/navigation/goals/${goalId}`)
}

/**
 * Compute avoidance maneuver
 */
export async function computeAvoidanceManeuver(
  request: DynamicObstacleAvoidanceRequest
): Promise<AvoidanceManeuver> {
  const res = await fetch(`${API_BASE}/api/navigation/avoid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.ok) {
    throw new Error(`Failed to compute avoidance: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Update detected obstacles for robot
 */
export async function updateObstacles(
  robotId: string,
  obstacles: Obstacle[]
): Promise<{ status: string; robot_id: string; obstacle_count: number }> {
  const res = await fetch(`${API_BASE}/api/navigation/obstacles/${robotId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(obstacles),
  })

  if (!res.ok) {
    throw new Error(`Failed to update obstacles: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get current obstacles for robot
 */
export async function fetchObstacles(robotId: string): Promise<Obstacle[]> {
  return fetchJson<Obstacle[]>(`/api/navigation/obstacles/${robotId}`)
}

/**
 * Plan formation navigation
 */
export async function planFormationNavigation(
  request: FormationNavigationRequest
): Promise<Record<string, PlannedPath>> {
  const res = await fetch(`${API_BASE}/api/navigation/formation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.ok) {
    throw new Error(`Failed to plan formation: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Adapt navigation to context
 */
export async function adaptToContext(
  request: ContextAdaptationRequest
): Promise<AdaptedNavigationParams> {
  const res = await fetch(`${API_BASE}/api/navigation/adapt-context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.ok) {
    throw new Error(`Failed to adapt context: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Update navigation status
 */
export async function updateNavigationStatus(status: NavigationStatus): Promise<NavigationStatus> {
  const res = await fetch(`${API_BASE}/api/navigation/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(status),
  })

  if (!res.ok) {
    throw new Error(`Failed to update status: ${res.statusText}`)
  }

  return res.json()
}

/**
 * Get navigation status for robot
 */
export async function fetchNavigationStatus(robotId: string): Promise<NavigationStatus> {
  return fetchJson<NavigationStatus>(`/api/navigation/status/${robotId}`)
}

/**
 * Get social navigation parameters
 */
export async function fetchSocialParams(): Promise<SocialNavigationParams> {
  return fetchJson<SocialNavigationParams>("/api/navigation/social-params")
}

/**
 * Update social navigation parameters
 */
export async function updateSocialParams(params: SocialNavigationParams): Promise<SocialNavigationParams> {
  const res = await fetch(`${API_BASE}/api/navigation/social-params`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    throw new Error(`Failed to update social params: ${res.statusText}`)
  }

  return res.json()
}
