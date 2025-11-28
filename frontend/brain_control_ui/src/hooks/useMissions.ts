// frontend/brain_control_ui/src/hooks/useMissions.ts
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  brainApi,
  type MissionsInfo,
  type MissionsHealth,
  type MissionQueueEntry,
  type MissionEnqueuePayload,
  type MissionEnqueueResponse,
} from "@/lib/brainApi";

/* ------------------------------------------------------------------
   READ HOOKS – Info / Health / Queue / Agents
-------------------------------------------------------------------*/

/**
 * Metainformationen zum Missionssystem
 * GET /api/missions/info
 */
export function useMissionsInfo() {
  return useQuery<MissionsInfo>({
    queryKey: ["missions", "info"],
    queryFn: () => brainApi.missions.info(),
    refetchInterval: 30_000,
  });
}

/**
 * Health-Status der Missions-Worker
 * GET /api/missions/health
 */
export function useMissionsHealth() {
  return useQuery<MissionsHealth>({
    queryKey: ["missions", "health"],
    queryFn: () => brainApi.missions.health(),
    refetchInterval: 10_000,
  });
}

/**
 * Alias, damit Komponenten `useMissionHealth()` verwenden können.
 */
export function useMissionHealth() {
  return useMissionsHealth();
}

/**
 * Vorschau der Missionsqueue
 * GET /api/missions/queue
 */
export function useMissionsQueuePreview() {
  return useQuery<MissionQueueEntry[]>({
    queryKey: ["missions", "queue-preview"],
    queryFn: () => brainApi.missions.queuePreview(),
    refetchInterval: 8_000,
  });
}

/**
 * Alias, damit Komponenten `useMissionQueue()` verwenden können.
 */
export function useMissionQueue() {
  return useMissionsQueuePreview();
}

/**
 * Info über Missions-Agents
 * GET /api/missions/agents/info
 */
export function useMissionsAgentsInfo() {
  return useQuery<any>({
    queryKey: ["missions", "agents", "info"],
    queryFn: () => brainApi.missions.agentsInfo(),
    refetchInterval: 15_000,
  });
}

/* ------------------------------------------------------------------
   MUTATION – Mission enqueuen
-------------------------------------------------------------------*/

export function useMissionEnqueue() {
  const qc = useQueryClient();

  return useMutation<MissionEnqueueResponse, Error, MissionEnqueuePayload>({
    mutationKey: ["missions", "enqueue"],
    mutationFn: (payload) => brainApi.missions.enqueue(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["missions", "queue-preview"] });
    },
  });
}
/* ------------------------------------------------------------------
   Weitere Hooks (z.B. Mission Status etc.) können in useMission.ts
   definiert werden, da sie missionspezifisch sind.
-------------------------------------------------------------------*/