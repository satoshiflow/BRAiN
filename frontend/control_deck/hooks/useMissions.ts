/**
 * React Query hooks for Missions data
 *
 * Provides cached, auto-refetching queries and mutations for mission operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchMissions,
  createMission,
  updateMission,
  type Mission,
  type CreateMissionPayload,
  type UpdateMissionPayload,
} from '@/lib/missionsApi';

/**
 * Fetch all missions
 * Refetches every 10 seconds for real-time updates
 */
export function useMissions() {
  return useQuery<Mission[]>({
    queryKey: ['missions', 'list'],
    queryFn: fetchMissions,
    refetchInterval: 10_000,
    staleTime: 5_000,
    retry: 2,
  });
}

/**
 * Create new mission mutation
 * Automatically invalidates mission queries on success
 */
export function useCreateMission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateMissionPayload) => createMission(payload),
    onSuccess: () => {
      // Invalidate all mission-related queries
      queryClient.invalidateQueries({ queryKey: ['missions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'missions'] });
    },
  });
}

/**
 * Update mission mutation
 * Automatically invalidates mission queries on success
 */
export function useUpdateMission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateMissionPayload;
    }) => updateMission(id, payload),
    onSuccess: () => {
      // Invalidate all mission-related queries
      queryClient.invalidateQueries({ queryKey: ['missions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'missions'] });
    },
  });
}

/**
 * Filter missions by status
 * Client-side filtering using cached data
 */
export function useMissionsByStatus(status?: Mission['status']) {
  const { data: missions, ...rest } = useMissions();

  const filtered = missions?.filter((m) =>
    status ? m.status === status : true
  );

  return {
    data: filtered,
    ...rest,
  };
}

/**
 * Count missions by status
 * Useful for statistics dashboards
 */
export function useMissionCounts() {
  const { data: missions } = useMissions();

  if (!missions) {
    return {
      total: 0,
      running: 0,
      pending: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    };
  }

  return {
    total: missions.length,
    running: missions.filter((m) => m.status === 'RUNNING').length,
    pending: missions.filter((m) => m.status === 'PENDING').length,
    completed: missions.filter((m) => m.status === 'COMPLETED').length,
    failed: missions.filter((m) => m.status === 'FAILED').length,
    cancelled: missions.filter((m) => m.status === 'CANCELLED').length,
  };
}
