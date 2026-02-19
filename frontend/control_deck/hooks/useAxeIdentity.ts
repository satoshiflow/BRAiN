// React Query hooks for AXE Identities
// Provides data fetching, caching, and mutations

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  fetchIdentities,
  fetchIdentity,
  fetchActiveIdentity,
  createIdentity,
  updateIdentity,
  activateIdentity,
  deleteIdentity,
  type AXEIdentityCreate,
  type AXEIdentityUpdate,
  type AXEIdentity,
} from "@/lib/axeIdentityApi";

// ============================================================================
// Query Keys
// ============================================================================

export const identityKeys = {
  all: ["identities"] as const,
  lists: () => [...identityKeys.all, "list"] as const,
  list: (filters?: { search?: string }) =>
    [...identityKeys.lists(), { filters }] as const,
  active: () => [...identityKeys.all, "active"] as const,
  details: () => [...identityKeys.all, "detail"] as const,
  detail: (id: string) => [...identityKeys.details(), id] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch all identities with optional filtering
 */
export function useAxeIdentities(search?: string) {
  return useQuery({
    queryKey: identityKeys.list({ search }),
    queryFn: () => fetchIdentities(),
    staleTime: 5000, // 5 seconds before refetching
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
  });
}

/**
 * Hook to fetch the active identity
 */
export function useActiveAxeIdentity() {
  return useQuery({
    queryKey: identityKeys.active(),
    queryFn: () => fetchActiveIdentity(),
    staleTime: 5000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch a single identity by ID
 */
export function useAxeIdentity(id: string) {
  return useQuery({
    queryKey: identityKeys.detail(id),
    queryFn: () => fetchIdentity(id),
    enabled: !!id,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook to create a new identity
 */
export function useCreateAxeIdentity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createIdentity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: identityKeys.lists() });
    },
  });
}

/**
 * Hook to update an existing identity
 */
export function useUpdateAxeIdentity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AXEIdentityUpdate }) =>
      updateIdentity(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: identityKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: identityKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: identityKeys.active() });
    },
  });
}

/**
 * Hook to activate an identity
 */
export function useActivateAxeIdentity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: activateIdentity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: identityKeys.lists() });
      queryClient.invalidateQueries({ queryKey: identityKeys.active() });
    },
  });
}

/**
 * Hook to delete an identity
 */
export function useDeleteAxeIdentity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteIdentity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: identityKeys.lists() });
      queryClient.invalidateQueries({ queryKey: identityKeys.active() });
    },
  });
}
