/**
 * Sovereign Mode React Query Hooks
 *
 * Provides type-safe data fetching and mutation hooks for sovereign mode operations.
 * Uses TanStack React Query for server state management.
 *
 * @module hooks/useSovereignMode
 * @version 1.0.0
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { brainApi } from "@/lib/brainApi";
import type {
  SovereignInfo,
  SovereignMode,
  SovereignStatistics,
  ModeChangeRequest,
  Bundle,
  BundleStatus,
  BundleLoadRequest,
  ValidationResult,
  NetworkCheckResult,
  ModeConfig,
  AuditEntry,
  BundleDiscoveryResult,
} from "@/types/sovereign";

// ============================================================================
// READ HOOKS - Info / Status / Statistics
// ============================================================================

/**
 * Get sovereign mode system information
 * GET /api/sovereign-mode/info
 *
 * @returns Query result with system info
 */
export function useSovereignInfo() {
  return useQuery<SovereignInfo>({
    queryKey: ["sovereign", "info"],
    queryFn: () => brainApi.sovereignMode.info(),
    staleTime: 5 * 60 * 1000, // 5 minutes (rarely changes)
  });
}

/**
 * Get current sovereign mode status
 * GET /api/sovereign-mode/status
 *
 * Includes mode, network state, active bundle, and statistics.
 * Refreshes every 10 seconds for real-time updates.
 *
 * @returns Query result with current status
 */
export function useSovereignStatus() {
  return useQuery<SovereignMode>({
    queryKey: ["sovereign", "status"],
    queryFn: () => brainApi.sovereignMode.status(),
    refetchInterval: 10_000, // 10 seconds
  });
}

/**
 * Get comprehensive sovereign mode statistics
 * GET /api/sovereign-mode/statistics
 *
 * @returns Query result with statistics
 */
export function useSovereignStatistics() {
  return useQuery<SovereignStatistics>({
    queryKey: ["sovereign", "statistics"],
    queryFn: () => brainApi.sovereignMode.getStatistics(),
    refetchInterval: 15_000, // 15 seconds
  });
}

// ============================================================================
// BUNDLE HOOKS
// ============================================================================

/**
 * List available bundles
 * GET /api/sovereign-mode/bundles
 *
 * @param status Optional filter by bundle status
 * @returns Query result with bundle list
 */
export function useBundles(status?: BundleStatus) {
  return useQuery<Bundle[]>({
    queryKey: ["sovereign", "bundles", status ?? "all"],
    queryFn: () => brainApi.sovereignMode.listBundles(status),
    refetchInterval: 30_000, // 30 seconds
  });
}

/**
 * Get details for a specific bundle
 * GET /api/sovereign-mode/bundles/{id}
 *
 * @param bundleId Bundle identifier
 * @param enabled Whether to enable the query
 * @returns Query result with bundle details
 */
export function useBundle(bundleId: string | null, enabled = true) {
  return useQuery<Bundle>({
    queryKey: ["sovereign", "bundles", bundleId],
    queryFn: () => brainApi.sovereignMode.getBundle(bundleId!),
    enabled: enabled && bundleId !== null,
    refetchInterval: 20_000, // 20 seconds
  });
}

// ============================================================================
// NETWORK HOOKS
// ============================================================================

/**
 * Check network connectivity
 * GET /api/sovereign-mode/network/check
 *
 * @returns Query result with network check result
 */
export function useNetworkCheck() {
  return useQuery<NetworkCheckResult>({
    queryKey: ["sovereign", "network", "check"],
    queryFn: () => brainApi.sovereignMode.checkNetwork(),
    refetchInterval: 30_000, // 30 seconds
  });
}

// ============================================================================
// CONFIGURATION HOOKS
// ============================================================================

/**
 * Get sovereign mode configuration
 * GET /api/sovereign-mode/config
 *
 * @returns Query result with configuration
 */
export function useSovereignConfig() {
  return useQuery<ModeConfig>({
    queryKey: ["sovereign", "config"],
    queryFn: () => brainApi.sovereignMode.getConfig(),
    refetchInterval: 20_000, // 20 seconds
  });
}

// ============================================================================
// AUDIT HOOKS
// ============================================================================

/**
 * Get audit log entries
 * GET /api/sovereign-mode/audit
 *
 * @param limit Maximum entries to return (default: 100)
 * @param eventType Optional filter by event type
 * @returns Query result with audit entries
 */
export function useAuditLog(limit = 100, eventType?: string) {
  return useQuery<AuditEntry[]>({
    queryKey: ["sovereign", "audit", limit, eventType ?? "all"],
    queryFn: () => brainApi.sovereignMode.getAuditLog(limit, eventType),
    refetchInterval: 15_000, // 15 seconds
  });
}

// ============================================================================
// MUTATION HOOKS - Mode Changes, Bundle Operations
// ============================================================================

/**
 * Change operation mode
 * POST /api/sovereign-mode/mode
 *
 * Switches between ONLINE, OFFLINE, SOVEREIGN, and QUARANTINE modes.
 * Invalidates status queries on success.
 *
 * @returns Mutation hook for mode changes
 */
export function useModeChange() {
  const queryClient = useQueryClient();

  return useMutation<SovereignMode, Error, ModeChangeRequest>({
    mutationKey: ["sovereign", "mode-change"],
    mutationFn: (request) => brainApi.sovereignMode.changeMode(request),
    onSuccess: () => {
      // Invalidate all sovereign queries to refetch
      queryClient.invalidateQueries({ queryKey: ["sovereign", "status"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "statistics"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "audit"] });
    },
  });
}

/**
 * Load an offline bundle
 * POST /api/sovereign-mode/bundles/load
 *
 * Validates and loads a bundle. Invalidates bundle queries on success.
 *
 * @returns Mutation hook for bundle loading
 */
export function useBundleLoad() {
  const queryClient = useQueryClient();

  return useMutation<Bundle, Error, BundleLoadRequest>({
    mutationKey: ["sovereign", "bundle-load"],
    mutationFn: (request) => brainApi.sovereignMode.loadBundle(request),
    onSuccess: (data) => {
      // Invalidate affected queries
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles", data.id] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "status"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "statistics"] });
    },
  });
}

/**
 * Validate a bundle
 * POST /api/sovereign-mode/bundles/{id}/validate
 *
 * Checks SHA256 hashes for integrity. Can force revalidation.
 *
 * @returns Mutation hook for bundle validation
 */
export function useBundleValidate() {
  const queryClient = useQueryClient();

  return useMutation<ValidationResult, Error, { bundleId: string; force?: boolean }>({
    mutationKey: ["sovereign", "bundle-validate"],
    mutationFn: ({ bundleId, force }) => brainApi.sovereignMode.validateBundle(bundleId, force),
    onSuccess: (_, variables) => {
      // Invalidate bundle queries
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles", variables.bundleId] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "statistics"] });
    },
  });
}

/**
 * Discover bundles in bundles directory
 * POST /api/sovereign-mode/bundles/discover
 *
 * Scans for new or updated bundles. Invalidates bundle queries on success.
 *
 * @returns Mutation hook for bundle discovery
 */
export function useBundleDiscover() {
  const queryClient = useQueryClient();

  return useMutation<BundleDiscoveryResult, Error, void>({
    mutationKey: ["sovereign", "bundle-discover"],
    mutationFn: () => brainApi.sovereignMode.discoverBundles(),
    onSuccess: () => {
      // Invalidate bundle queries to show newly discovered bundles
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "statistics"] });
    },
  });
}

/**
 * Remove bundle from quarantine
 * DELETE /api/sovereign-mode/bundles/{id}/quarantine
 *
 * **Warning:** Only use if certain the bundle is safe.
 * Bundle will be reset to PENDING status.
 *
 * @returns Mutation hook for quarantine removal
 */
export function useBundleRemoveQuarantine() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationKey: ["sovereign", "bundle-remove-quarantine"],
    mutationFn: (bundleId) => brainApi.sovereignMode.removeQuarantine(bundleId),
    onSuccess: (_, bundleId) => {
      // Invalidate bundle queries
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "bundles", bundleId] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "statistics"] });
    },
  });
}

/**
 * Update sovereign mode configuration
 * PUT /api/sovereign-mode/config
 *
 * Updates configuration fields. Changes are persisted.
 *
 * @returns Mutation hook for config updates
 */
export function useConfigUpdate() {
  const queryClient = useQueryClient();

  return useMutation<ModeConfig, Error, Partial<ModeConfig>>({
    mutationKey: ["sovereign", "config-update"],
    mutationFn: (updates) => brainApi.sovereignMode.updateConfig(updates),
    onSuccess: () => {
      // Invalidate config query
      queryClient.invalidateQueries({ queryKey: ["sovereign", "config"] });
      queryClient.invalidateQueries({ queryKey: ["sovereign", "status"] });
    },
  });
}
