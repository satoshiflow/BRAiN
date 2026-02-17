/**
 * React Query hooks for Course Factory
 *
 * Template system for courses, learning paths, and educational content
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from "@/lib/api";


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
// API Functions
// ============================================================================

async function fetchCourseStats(): Promise<CourseStats> {
  const response = await fetch(`${API_BASE}/api/courses/stats`);
  if (!response.ok) {
    throw new Error(`Failed to fetch course stats: ${response.statusText}`);
  }
  const data = await response.json();

  // Get templates for additional stats
  const templatesResponse = await fetch(`${API_BASE}/api/courses/templates`);
  if (!templatesResponse.ok) {
    throw new Error(`Failed to fetch templates: ${templatesResponse.statusText}`);
  }
  const templatesData = await templatesResponse.json();
  const templates = templatesData.courses || [];

  const templatesByCategory = templates.reduce((acc: Record<string, number>, t: any) => {
    const category = t.category || 'Uncategorized';
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {});

  const templatesByDifficulty = templates.reduce((acc: Record<DifficultyLevel, number>, t: any) => {
    const difficulty = t.difficulty_level || 'beginner';
    acc[difficulty as DifficultyLevel] = (acc[difficulty as DifficultyLevel] || 0) + 1;
    return acc;
  }, {} as Record<DifficultyLevel, number>);

  const totalDuration = templates.reduce((sum: number, t: any) => sum + (t.estimated_duration_hours || 0), 0);

  return {
    total_templates: data.total_courses || 0,
    published: data.published_courses || 0,
    draft: data.draft_courses || 0,
    archived: 0,
    templates_by_category: templatesByCategory,
    templates_by_difficulty: templatesByDifficulty,
    total_modules: data.total_modules || 0,
    total_lessons: data.total_lessons || 0,
    average_duration_hours: templates.length > 0 ? totalDuration / templates.length : 0,
  };
}

async function fetchCourseTemplates(): Promise<CourseTemplate[]> {
  const response = await fetch(`${API_BASE}/api/courses/templates`);
  if (!response.ok) {
    throw new Error(`Failed to fetch course templates: ${response.statusText}`);
  }
  const data = await response.json();
  return data.courses || [];
}

async function fetchCourseTemplate(id: string): Promise<CourseTemplate> {
  const response = await fetch(`${API_BASE}/api/courses/templates/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch course template: ${response.statusText}`);
  }
  return await response.json();
}

async function createCourseTemplate(request: CreateCourseRequest): Promise<CourseTemplate> {
  const response = await fetch(`${API_BASE}/api/courses/templates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to create course template: ${response.statusText}`);
  }
  return await response.json();
}

async function updateCourseTemplate(id: string, request: UpdateCourseRequest): Promise<CourseTemplate> {
  const response = await fetch(`${API_BASE}/api/courses/templates/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to update course template: ${response.statusText}`);
  }
  return await response.json();
}

async function deleteCourseTemplate(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/courses/templates/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete course template: ${response.statusText}`);
  }
}

async function duplicateCourseTemplate(id: string, newName: string): Promise<DuplicateCourseResponse> {
  // Fetch original template
  const original = await fetchCourseTemplate(id);

  // Create duplicate with new name
  const duplicate: CreateCourseRequest = {
    name: newName,
    description: original.description,
    category: original.category,
    difficulty: original.difficulty,
    status: 'draft',
    modules: original.modules,
    prerequisites: original.prerequisites,
    learning_objectives: original.learning_objectives,
    tags: original.tags,
  };

  const newTemplate = await createCourseTemplate(duplicate);

  return {
    id: newTemplate.id,
    name: newTemplate.name,
    message: `Successfully duplicated course template as "${newName}"`,
  };
}

async function publishCourseTemplate(id: string): Promise<CourseTemplate> {
  const response = await fetch(`${API_BASE}/api/courses/templates/${id}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ publish: true }),
  });
  if (!response.ok) {
    throw new Error(`Failed to publish course template: ${response.statusText}`);
  }
  return await response.json();
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
