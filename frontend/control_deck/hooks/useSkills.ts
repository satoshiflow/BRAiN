// React Query hooks for Skills
// Provides data fetching, caching, and mutations

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  fetchSkills,
  fetchSkill,
  fetchSkillCategories,
  createSkill,
  updateSkill,
  deleteSkill,
  executeSkill,
  type CreateSkillPayload,
  type UpdateSkillPayload,
  type Skill,
  type SkillCategory,
} from "@/lib/skillsApi";

// ============================================================================
// Query Keys
// ============================================================================

export const skillKeys = {
  all: ["skills"] as const,
  lists: () => [...skillKeys.all, "list"] as const,
  list: (category?: SkillCategory | "all", search?: string) =>
    [...skillKeys.lists(), { category, search }] as const,
  categories: () => [...skillKeys.all, "categories"] as const,
  details: () => [...skillKeys.all, "detail"] as const,
  detail: (id: string) => [...skillKeys.details(), id] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch all skills with optional filtering
 */
export function useSkills(category?: SkillCategory | "all", search?: string) {
  return useQuery({
    queryKey: skillKeys.list(category, search),
    queryFn: () => fetchSkills(category, search),
    staleTime: 5000, // 5 seconds before refetching
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
  });
}

/**
 * Hook to fetch a single skill by ID
 */
export function useSkill(id: string) {
  return useQuery({
    queryKey: skillKeys.detail(id),
    queryFn: () => fetchSkill(id),
    enabled: !!id,
  });
}

/**
 * Hook to fetch all skill categories
 */
export function useSkillCategories() {
  return useQuery({
    queryKey: skillKeys.categories(),
    queryFn: fetchSkillCategories,
    staleTime: 30000, // Categories rarely change
    refetchOnWindowFocus: false,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook to create a new skill
 */
export function useCreateSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createSkill,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skillKeys.lists() });
    },
  });
}

/**
 * Hook to update an existing skill
 */
export function useUpdateSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSkillPayload }) =>
      updateSkill(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: skillKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: skillKeys.detail(variables.id),
      });
    },
  });
}

/**
 * Hook to delete a skill
 */
export function useDeleteSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSkill,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skillKeys.lists() });
    },
  });
}

/**
 * Hook to execute a skill
 */
export function useExecuteSkill() {
  return useMutation({
    mutationFn: ({ id, parameters }: { id: string; parameters: Record<string, unknown> }) =>
      executeSkill(id, parameters),
  });
}
