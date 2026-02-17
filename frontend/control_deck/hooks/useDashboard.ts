/**
 * React Query hooks for Dashboard data
 *
 * Replaces useState+useEffect patterns with cached, auto-refetching queries
 */

import { useQuery } from '@tanstack/react-query';
import {
  fetchCoreHealth,
  fetchMissionsHealth,
  fetchSupervisorHealth,
  fetchMissionsOverviewStats,
  fetchThreatsOverviewStats,
  fetchImmuneHealth,
  type CoreHealth,
  type MissionsHealth,
  type SupervisorHealth,
  type MissionsOverviewStats,
  type ThreatsOverviewStats,
  type ImmuneHealthSummary,
} from '@/lib/dashboardApi';

/**
 * Core API health status
 * Refetches every 30 seconds
 */
export function useCoreHealth() {
  return useQuery<CoreHealth>({
    queryKey: ['dashboard', 'core', 'health'],
    queryFn: fetchCoreHealth,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Missions system health
 * Refetches every 30 seconds
 */
export function useMissionsHealth() {
  return useQuery<MissionsHealth>({
    queryKey: ['dashboard', 'missions', 'health'],
    queryFn: fetchMissionsHealth,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Supervisor system health
 * Refetches every 30 seconds
 */
export function useSupervisorHealth() {
  return useQuery<SupervisorHealth>({
    queryKey: ['dashboard', 'supervisor', 'health'],
    queryFn: fetchSupervisorHealth,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Missions overview statistics
 * Refetches every 15 seconds (more frequent for active data)
 */
export function useMissionsStats() {
  return useQuery<MissionsOverviewStats>({
    queryKey: ['dashboard', 'missions', 'stats'],
    queryFn: fetchMissionsOverviewStats,
    refetchInterval: 15_000,
    staleTime: 10_000,
    retry: 2,
  });
}

/**
 * Threats overview statistics
 * Refetches every 30 seconds
 */
export function useThreatsStats() {
  return useQuery<ThreatsOverviewStats>({
    queryKey: ['dashboard', 'threats', 'stats'],
    queryFn: fetchThreatsOverviewStats,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Immune system health summary
 * Refetches every 30 seconds
 */
export function useImmuneHealth() {
  return useQuery<ImmuneHealthSummary>({
    queryKey: ['dashboard', 'immune', 'health'],
    queryFn: fetchImmuneHealth,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Combined dashboard data hook
 * Fetches all dashboard data in parallel
 * Use individual hooks above if you only need specific data
 */
export function useDashboardData() {
  const coreHealth = useCoreHealth();
  const missionsHealth = useMissionsHealth();
  const supervisorHealth = useSupervisorHealth();
  const missionsStats = useMissionsStats();
  const threatsStats = useThreatsStats();
  const immuneHealth = useImmuneHealth();

  return {
    coreHealth,
    missionsHealth,
    supervisorHealth,
    missionsStats,
    threatsStats,
    immuneHealth,
    // Aggregate loading/error states
    isLoading:
      coreHealth.isLoading ||
      missionsHealth.isLoading ||
      supervisorHealth.isLoading ||
      missionsStats.isLoading ||
      threatsStats.isLoading ||
      immuneHealth.isLoading,
    isError:
      coreHealth.isError ||
      missionsHealth.isError ||
      supervisorHealth.isError ||
      missionsStats.isError ||
      threatsStats.isError ||
      immuneHealth.isError,
    errors: [
      coreHealth.error,
      missionsHealth.error,
      supervisorHealth.error,
      missionsStats.error,
      threatsStats.error,
      immuneHealth.error,
    ].filter(Boolean),
  };
}
