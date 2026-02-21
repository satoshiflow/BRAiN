// React Hooks für BRAiN API
// TanStack Query Integration

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, queryKeys, type Mission, type MissionHealth, type SystemEvent, type EventStats, type WorkerStatus } from '@/lib/api';

// Missions Hooks
export function useMissions(limit = 20) {
  return useQuery({
    queryKey: queryKeys.missions.queue(limit),
    queryFn: () => api.missions.getQueue(limit),
    refetchInterval: 5000, // Alle 5 Sekunden
  });
}

export function useMissionHealth() {
  return useQuery({
    queryKey: queryKeys.missions.health,
    queryFn: () => api.missions.getHealth(),
    refetchInterval: 10000, // Alle 10 Sekunden
  });
}

export function useWorkerStatus() {
  return useQuery({
    queryKey: queryKeys.missions.worker,
    queryFn: () => api.missions.getWorkerStatus(),
    refetchInterval: 30000, // Alle 30 Sekunden
  });
}

export function useMissionEvents(limit = 100) {
  return useQuery({
    queryKey: queryKeys.missions.events(limit),
    queryFn: () => api.missions.getEvents(limit),
    refetchInterval: 5000,
  });
}

export function useEnqueueMission() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: api.missions.enqueue,
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: queryKeys.missions.all });
    },
  });
}

// Events Hooks
export function useEvents(params?: { 
  limit?: number; 
  offset?: number; 
  event_type?: string; 
  severity?: string;
}) {
  return useQuery({
    queryKey: queryKeys.events.all(params),
    queryFn: () => api.events.getAll(params),
    refetchInterval: 5000,
  });
}

export function useEventStats() {
  return useQuery({
    queryKey: queryKeys.events.stats,
    queryFn: () => api.events.getStats(),
    refetchInterval: 30000,
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: api.events.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
    },
  });
}

// Agents Hooks (Placeholder)
export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: () => api.agents.getAll(),
    refetchInterval: 10000,
  });
}

// Dashboard Aggregated Data
export function useDashboardData() {
  const missions = useMissions(10);
  const health = useMissionHealth();
  const events = useEvents({ limit: 50 });
  const eventStats = useEventStats();
  const worker = useWorkerStatus();

  const isLoading = missions.isLoading || health.isLoading || events.isLoading;
  const isError = missions.isError || health.isError || events.isError;

  // Berechne KPIs
  const activeMissions = missions.data?.items.filter(
    (m: Mission) => m.status === 'running'
  ).length ?? 0;

  const pendingMissions = missions.data?.items.filter(
    (m: Mission) => m.status === 'pending'
  ).length ?? 0;

  const failedMissions = missions.data?.items.filter(
    (m: Mission) => m.status === 'failed'
  ).length ?? 0;

  const recentEvents = events.data?.slice(0, 10) ?? [];

  const errorEvents = events.data?.filter(
    (e: SystemEvent) => e.severity === 'error' || e.severity === 'critical'
  ).length ?? 0;

  return {
    isLoading,
    isError,
    data: {
      missions: {
        total: missions.data?.length ?? 0,
        active: activeMissions,
        pending: pendingMissions,
        failed: failedMissions,
        items: missions.data?.items ?? [],
      },
      health: health.data,
      worker: worker.data,
      events: {
        recent: recentEvents,
        errorCount: errorEvents,
        stats: eventStats.data,
      },
    },
    refetch: () => {
      missions.refetch();
      health.refetch();
      events.refetch();
      eventStats.refetch();
    },
  };
}