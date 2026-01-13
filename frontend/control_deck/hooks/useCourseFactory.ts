/**
 * React Query hooks for Course Factory
 *
 * Template system for courses, learning paths, and educational content
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type CourseStatus = 'draft' | 'published' | 'archived';

export interface CourseModule {
  id: string;
  title: string;
  description: string;
  order: number;
  duration_minutes?: number;
  lessons: Lesson[];
}

export interface Lesson {
  id: string;
  title: string;
  content: string;
  type: 'text' | 'video' | 'interactive' | 'quiz';
  duration_minutes?: number;
  order: number;
  resources?: Resource[];
}

export interface Resource {
  id: string;
  title: string;
  type: 'document' | 'video' | 'link' | 'code';
  url: string;
}

export interface CourseTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: DifficultyLevel;
  status: CourseStatus;
  duration_hours?: number;
  modules: CourseModule[];
  prerequisites?: string[];
  learning_objectives?: string[];
  tags?: string[];
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  usage_count?: number;
}

export interface CourseStats {
  total_templates: number;
  published: number;
  draft: number;
  archived: number;
  templates_by_category: Record<string, number>;
  templates_by_difficulty: Record<DifficultyLevel, number>;
  total_modules: number;
  total_lessons: number;
  average_duration_hours?: number;
}

export interface CreateCourseRequest {
  name: string;
  description: string;
  category: string;
  difficulty: DifficultyLevel;
  status?: CourseStatus;
  modules?: CourseModule[];
  prerequisites?: string[];
  learning_objectives?: string[];
  tags?: string[];
}

export interface UpdateCourseRequest {
  name?: string;
  description?: string;
  category?: string;
  difficulty?: DifficultyLevel;
  status?: CourseStatus;
  modules?: CourseModule[];
  prerequisites?: string[];
  learning_objectives?: string[];
  tags?: string[];
}

export interface DuplicateCourseResponse {
  id: string;
  name: string;
  message: string;
}

// ============================================================================
// API Functions (Placeholder - will be implemented when backend is ready)
// ============================================================================

async function fetchCourseStats(): Promise<CourseStats> {
  // TODO: Implement when backend endpoint is ready
  // For now, return mock data
  return {
    total_templates: 12,
    published: 8,
    draft: 3,
    archived: 1,
    templates_by_category: {
      'Programming': 5,
      'AI/ML': 3,
      'DevOps': 2,
      'Business': 2,
    },
    templates_by_difficulty: {
      beginner: 4,
      intermediate: 5,
      advanced: 2,
      expert: 1,
    },
    total_modules: 45,
    total_lessons: 178,
    average_duration_hours: 12.5,
  };
}

async function fetchCourseTemplates(): Promise<CourseTemplate[]> {
  // TODO: Implement when backend endpoint is ready
  return [];
}

async function fetchCourseTemplate(id: string): Promise<CourseTemplate> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function createCourseTemplate(request: CreateCourseRequest): Promise<CourseTemplate> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function updateCourseTemplate(id: string, request: UpdateCourseRequest): Promise<CourseTemplate> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function deleteCourseTemplate(id: string): Promise<void> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function duplicateCourseTemplate(id: string, newName: string): Promise<DuplicateCourseResponse> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function publishCourseTemplate(id: string): Promise<CourseTemplate> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get course factory statistics
 */
export function useCourseStats() {
  return useQuery<CourseStats>({
    queryKey: ['courses', 'stats'],
    queryFn: fetchCourseStats,
    refetchInterval: 60_000, // Refresh every minute
    staleTime: 30_000,
    retry: 2,
  });
}

/**
 * Get all course templates
 */
export function useCourseTemplates() {
  return useQuery<CourseTemplate[]>({
    queryKey: ['courses', 'templates'],
    queryFn: fetchCourseTemplates,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Get single course template by ID
 */
export function useCourseTemplate(id: string) {
  return useQuery<CourseTemplate>({
    queryKey: ['courses', 'templates', id],
    queryFn: () => fetchCourseTemplate(id),
    enabled: !!id,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Create new course template
 */
export function useCreateCourseTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createCourseTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses', 'templates'] });
      queryClient.invalidateQueries({ queryKey: ['courses', 'stats'] });
    },
  });
}

/**
 * Update course template
 */
export function useUpdateCourseTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: UpdateCourseRequest }) =>
      updateCourseTemplate(id, request),
    onSuccess: (data) => {
      queryClient.setQueryData(['courses', 'templates', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['courses', 'templates'] });
      queryClient.invalidateQueries({ queryKey: ['courses', 'stats'] });
    },
  });
}

/**
 * Delete course template
 */
export function useDeleteCourseTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCourseTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses', 'templates'] });
      queryClient.invalidateQueries({ queryKey: ['courses', 'stats'] });
    },
  });
}

/**
 * Duplicate course template
 */
export function useDuplicateCourseTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, newName }: { id: string; newName: string }) =>
      duplicateCourseTemplate(id, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses', 'templates'] });
      queryClient.invalidateQueries({ queryKey: ['courses', 'stats'] });
    },
  });
}

/**
 * Publish course template
 */
export function usePublishCourseTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: publishCourseTemplate,
    onSuccess: (data) => {
      queryClient.setQueryData(['courses', 'templates', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['courses', 'templates'] });
      queryClient.invalidateQueries({ queryKey: ['courses', 'stats'] });
    },
  });
}

/**
 * Helper hook: Get templates by category
 */
export function useCourseTemplatesByCategory(category?: string) {
  const { data: templates } = useCourseTemplates();

  if (!category || !templates) return templates ?? [];

  return templates.filter((t) => t.category === category);
}

/**
 * Helper hook: Get templates by difficulty
 */
export function useCourseTemplatesByDifficulty(difficulty?: DifficultyLevel) {
  const { data: templates } = useCourseTemplates();

  if (!difficulty || !templates) return templates ?? [];

  return templates.filter((t) => t.difficulty === difficulty);
}

/**
 * Helper hook: Get templates by status
 */
export function useCourseTemplatesByStatus(status?: CourseStatus) {
  const { data: templates } = useCourseTemplates();

  if (!status || !templates) return templates ?? [];

  return templates.filter((t) => t.status === status);
}

/**
 * Helper hook: Search templates by name or description
 */
export function useSearchCourseTemplates(query: string) {
  const { data: templates } = useCourseTemplates();

  if (!query || !templates) return templates ?? [];

  const lowercaseQuery = query.toLowerCase();
  return templates.filter(
    (t) =>
      t.name.toLowerCase().includes(lowercaseQuery) ||
      t.description.toLowerCase().includes(lowercaseQuery) ||
      t.tags?.some((tag) => tag.toLowerCase().includes(lowercaseQuery))
  );
}
