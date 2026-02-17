// React Query hooks for Mission Templates
// Provides data fetching, caching, and mutations

import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryKey,
} from "@tanstack/react-query";
import {
  fetchTemplates,
  fetchTemplate,
  fetchTemplateCategories,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  instantiateTemplate,
  type CreateTemplatePayload,
  type UpdateTemplatePayload,
  type InstantiateTemplatePayload,
  type MissionTemplate,
} from "@/lib/missionTemplatesApi";

// ============================================================================
// Query Keys
// ============================================================================

export const templateKeys = {
  all: ["mission-templates"] as const,
  lists: () => [...templateKeys.all, "list"] as const,
  list: (category?: string, search?: string) =>
    [...templateKeys.lists(), { category, search }] as const,
  categories: () => [...templateKeys.all, "categories"] as const,
  details: () => [...templateKeys.all, "detail"] as const,
  detail: (id: string) => [...templateKeys.details(), id] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch all mission templates with optional filtering
 */
export function useTemplates(category?: string, search?: string) {
  return useQuery({
    queryKey: templateKeys.list(category, search),
    queryFn: () => fetchTemplates(category, search),
  });
}

/**
 * Hook to fetch all template categories
 */
export function useTemplateCategories() {
  return useQuery({
    queryKey: templateKeys.categories(),
    queryFn: fetchTemplateCategories,
  });
}

/**
 * Hook to fetch a single template by ID
 */
export function useTemplate(templateId: string) {
  return useQuery({
    queryKey: templateKeys.detail(templateId),
    queryFn: () => fetchTemplate(templateId),
    enabled: !!templateId,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook to create a new template
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTemplate,
    onSuccess: () => {
      // Invalidate template lists to refresh
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
      queryClient.invalidateQueries({ queryKey: templateKeys.categories() });
    },
  });
}

/**
 * Hook to update an existing template
 */
export function useUpdateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateTemplatePayload;
    }) => updateTemplate(id, payload),
    onSuccess: (_, variables) => {
      // Invalidate the specific template and all lists
      queryClient.invalidateQueries({
        queryKey: templateKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

/**
 * Hook to delete a template
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
      queryClient.invalidateQueries({ queryKey: templateKeys.categories() });
    },
  });
}

/**
 * Hook to instantiate a template into a mission
 */
export function useInstantiateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: InstantiateTemplatePayload;
    }) => instantiateTemplate(id, payload),
    onSuccess: () => {
      // Invalidate missions list when a new mission is created
      queryClient.invalidateQueries({ queryKey: ["missions"] });
    },
  });
}
