/**
 * React Query hooks for Fleet Management
 *
 * Multi-robot fleet coordination and management system
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export type RobotStatus = 'idle' | 'active' | 'charging' | 'maintenance' | 'error';

export interface Robot {
  id: string;
  name: string;
  status: RobotStatus;
  capabilities: string[];
  max_payload: number;
  battery_capacity: number;
  battery_level?: number;
  location?: {
    x: number;
    y: number;
    z?: number;
  };
  current_task_id?: string;
  tasks_completed?: number;
  created_at?: string;
  last_seen?: string;
}

export interface FleetStats {
  total_robots: number;
  active: number;
  idle: number;
  charging: number;
  maintenance: number;
  error: number;
  total_tasks_completed: number;
  total_tasks_pending: number;
  average_battery_level?: number;
}

export interface FleetInfo {
  name: string;
  version: string;
  description: string;
  fleet_size: number;
  coordination_zones: number;
}

export interface RegisterRobotRequest {
  id: string;
  name: string;
  capabilities: string[];
  max_payload: number;
  battery_capacity: number;
  location?: {
    x: number;
    y: number;
    z?: number;
  };
}

export interface UpdateRobotRequest {
  name?: string;
  status?: RobotStatus;
  capabilities?: string[];
  battery_level?: number;
  location?: {
    x: number;
    y: number;
    z?: number;
  };
  current_task_id?: string;
}

export interface AssignTaskRequest {
  task_id: string;
  robot_id?: string;
  requirements?: string[];
  priority?: 'low' | 'normal' | 'high' | 'critical';
}

export interface AssignTaskResponse {
  robot_id: string;
  task_id: string;
  assignment_time: string;
  estimated_completion?: string;
}

export interface CoordinationZone {
  id: string;
  name: string;
  area: {
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
  };
  max_robots: number;
  current_robots: number;
  robots: string[];
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchFleetInfo(): Promise<FleetInfo> {
  const response = await fetch(`${API_BASE}/api/fleet/info`);
  if (!response.ok) throw new Error(`Failed to fetch fleet info: ${response.statusText}`);
  return response.json();
}

async function fetchFleetStats(): Promise<FleetStats> {
  const response = await fetch(`${API_BASE}/api/fleet/stats`);
  if (!response.ok) throw new Error(`Failed to fetch fleet stats: ${response.statusText}`);
  return response.json();
}

async function fetchRobots(): Promise<Robot[]> {
  const response = await fetch(`${API_BASE}/api/fleet/robots`);
  if (!response.ok) throw new Error(`Failed to fetch robots: ${response.statusText}`);
  return response.json();
}

async function fetchRobot(id: string): Promise<Robot> {
  const response = await fetch(`${API_BASE}/api/fleet/robots/${id}`);
  if (!response.ok) throw new Error(`Failed to fetch robot: ${response.statusText}`);
  return response.json();
}

async function registerRobot(request: RegisterRobotRequest): Promise<Robot> {
  const response = await fetch(`${API_BASE}/api/fleet/robots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to register robot: ${response.statusText}`);
  return response.json();
}

async function updateRobot(id: string, request: UpdateRobotRequest): Promise<Robot> {
  const response = await fetch(`${API_BASE}/api/fleet/robots/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to update robot: ${response.statusText}`);
  return response.json();
}

async function deregisterRobot(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/fleet/robots/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`Failed to deregister robot: ${response.statusText}`);
}

async function assignTask(request: AssignTaskRequest): Promise<AssignTaskResponse> {
  const response = await fetch(`${API_BASE}/api/fleet/assign-task`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to assign task: ${response.statusText}`);
  return response.json();
}

async function fetchCoordinationZones(): Promise<CoordinationZone[]> {
  const response = await fetch(`${API_BASE}/api/fleet/zones`);
  if (!response.ok) throw new Error(`Failed to fetch zones: ${response.statusText}`);
  return response.json();
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get fleet system information
 */
export function useFleetInfo() {
  return useQuery<FleetInfo>({
    queryKey: ['fleet', 'info'],
    queryFn: fetchFleetInfo,
    staleTime: 300_000, // 5 minutes
    retry: 2,
  });
}

/**
 * Get fleet statistics with auto-refresh
 */
export function useFleetStats() {
  return useQuery<FleetStats>({
    queryKey: ['fleet', 'stats'],
    queryFn: fetchFleetStats,
    refetchInterval: 10_000, // Refresh every 10 seconds
    staleTime: 5_000,
    retry: 2,
  });
}

/**
 * Get all robots in fleet
 */
export function useRobots() {
  return useQuery<Robot[]>({
    queryKey: ['fleet', 'robots'],
    queryFn: fetchRobots,
    refetchInterval: 15_000, // Refresh every 15 seconds
    staleTime: 10_000,
    retry: 2,
  });
}

/**
 * Get single robot by ID
 */
export function useRobot(id: string) {
  return useQuery<Robot>({
    queryKey: ['fleet', 'robots', id],
    queryFn: () => fetchRobot(id),
    enabled: !!id,
    refetchInterval: 5_000, // Refresh every 5 seconds for active robot
    staleTime: 3_000,
    retry: 2,
  });
}

/**
 * Get coordination zones
 */
export function useCoordinationZones() {
  return useQuery<CoordinationZone[]>({
    queryKey: ['fleet', 'zones'],
    queryFn: fetchCoordinationZones,
    refetchInterval: 30_000, // Refresh every 30 seconds
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Register new robot in fleet
 */
export function useRegisterRobot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: registerRobot,
    onSuccess: () => {
      // Invalidate robots list and stats
      queryClient.invalidateQueries({ queryKey: ['fleet', 'robots'] });
      queryClient.invalidateQueries({ queryKey: ['fleet', 'stats'] });
    },
  });
}

/**
 * Update robot status/location/battery
 */
export function useUpdateRobot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: UpdateRobotRequest }) =>
      updateRobot(id, request),
    onSuccess: (data) => {
      // Update cache for specific robot
      queryClient.setQueryData(['fleet', 'robots', data.id], data);
      // Invalidate robots list and stats
      queryClient.invalidateQueries({ queryKey: ['fleet', 'robots'] });
      queryClient.invalidateQueries({ queryKey: ['fleet', 'stats'] });
    },
  });
}

/**
 * Deregister robot from fleet
 */
export function useDeregisterRobot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deregisterRobot,
    onSuccess: () => {
      // Invalidate robots list and stats
      queryClient.invalidateQueries({ queryKey: ['fleet', 'robots'] });
      queryClient.invalidateQueries({ queryKey: ['fleet', 'stats'] });
    },
  });
}

/**
 * Assign task to robot (optimal selection or specific robot)
 */
export function useAssignTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: assignTask,
    onSuccess: () => {
      // Invalidate robots list and stats (task assignments changed)
      queryClient.invalidateQueries({ queryKey: ['fleet', 'robots'] });
      queryClient.invalidateQueries({ queryKey: ['fleet', 'stats'] });
    },
  });
}

/**
 * Helper hook: Get robots by status
 */
export function useRobotsByStatus(status?: RobotStatus) {
  const { data: robots } = useRobots();

  if (!status || !robots) return robots ?? [];

  return robots.filter((r) => r.status === status);
}

/**
 * Helper hook: Get robots by capability
 */
export function useRobotsByCapability(capability: string) {
  const { data: robots } = useRobots();

  if (!robots) return [];

  return robots.filter((r) => r.capabilities.includes(capability));
}

/**
 * Helper hook: Get low battery robots
 */
export function useLowBatteryRobots(threshold: number = 20) {
  const { data: robots } = useRobots();

  if (!robots) return [];

  return robots.filter((r) => r.battery_level !== undefined && r.battery_level < threshold);
}
