/**
 * React Query hooks for Hardware Module
 *
 * Robot hardware control and state monitoring
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from "@/lib/api";


// ============================================================================
// Types
// ============================================================================

export interface HardwareInfo {
  name: string;
  version: string;
  description: string;
  supported_robots: string[];
}

export interface MovementCommand {
  direction: 'forward' | 'backward' | 'left' | 'right' | 'stop';
  speed?: number;
  duration_ms?: number;
}

export interface RobotHardwareState {
  robot_id: string;
  timestamp: string;
  motors: {
    left: {
      power: number;
      rpm: number;
      temperature: number;
    };
    right: {
      power: number;
      rpm: number;
      temperature: number;
    };
  };
  sensors: {
    ultrasonic?: {
      distance_cm: number;
      reliable: boolean;
    };
    infrared?: {
      obstacle_detected: boolean;
      distance_cm: number;
    };
    imu?: {
      acceleration: { x: number; y: number; z: number };
      gyroscope: { x: number; y: number; z: number };
      orientation: { roll: number; pitch: number; yaw: number };
    };
  };
  battery: {
    voltage: number;
    current: number;
    percentage: number;
    charging: boolean;
  };
  connectivity: {
    wifi_strength: number;
    latency_ms: number;
  };
}

export interface CommandResponse {
  robot_id: string;
  command_accepted: boolean;
  execution_time_ms: number;
  message: string;
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchHardwareInfo(): Promise<HardwareInfo> {
  const response = await fetch(`${API_BASE}/api/hardware/info`);
  if (!response.ok) throw new Error(`Failed to fetch hardware info: ${response.statusText}`);
  return response.json();
}

async function sendMovementCommand(robotId: string, command: MovementCommand): Promise<CommandResponse> {
  const response = await fetch(`${API_BASE}/api/hardware/robots/${robotId}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  });
  if (!response.ok) throw new Error(`Failed to send command: ${response.statusText}`);
  return response.json();
}

async function fetchRobotState(robotId: string): Promise<RobotHardwareState> {
  const response = await fetch(`${API_BASE}/api/hardware/robots/${robotId}/state`);
  if (!response.ok) throw new Error(`Failed to fetch robot state: ${response.statusText}`);
  return response.json();
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get hardware module information
 */
export function useHardwareInfo() {
  return useQuery<HardwareInfo>({
    queryKey: ['hardware', 'info'],
    queryFn: fetchHardwareInfo,
    staleTime: 300_000, // 5 minutes
    retry: 2,
  });
}

/**
 * Get robot hardware state
 */
export function useRobotState(robotId: string | undefined) {
  return useQuery<RobotHardwareState>({
    queryKey: ['hardware', 'state', robotId],
    queryFn: () => fetchRobotState(robotId!),
    enabled: !!robotId,
    refetchInterval: 2_000, // Very frequent for hardware monitoring
    staleTime: 1_000,
    retry: 2,
  });
}

/**
 * Send movement command to robot
 */
export function useSendCommand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ robotId, command }: { robotId: string; command: MovementCommand }) =>
      sendMovementCommand(robotId, command),
    onSuccess: (data) => {
      // Invalidate robot state to get fresh data
      queryClient.invalidateQueries({ queryKey: ['hardware', 'state', data.robot_id] });
    },
  });
}

/**
 * Helper hook: Check if robot motors are healthy
 */
export function useMotorHealth(robotId: string | undefined) {
  const { data: state } = useRobotState(robotId);

  if (!state) return null;

  const isHealthy =
    state.motors.left.temperature < 80 &&
    state.motors.right.temperature < 80 &&
    Math.abs(state.motors.left.rpm - state.motors.right.rpm) < 100; // Motor balance

  return { isHealthy, state };
}

/**
 * Helper hook: Quick movement commands
 */
export function useQuickCommands(robotId: string) {
  const sendCommand = useSendCommand();

  return {
    moveForward: () => sendCommand.mutate({ robotId, command: { direction: 'forward', speed: 1.0 } }),
    moveBackward: () => sendCommand.mutate({ robotId, command: { direction: 'backward', speed: 1.0 } }),
    turnLeft: () => sendCommand.mutate({ robotId, command: { direction: 'left', speed: 0.5 } }),
    turnRight: () => sendCommand.mutate({ robotId, command: { direction: 'right', speed: 0.5 } }),
    stop: () => sendCommand.mutate({ robotId, command: { direction: 'stop' } }),
    isPending: sendCommand.isPending,
  };
}
