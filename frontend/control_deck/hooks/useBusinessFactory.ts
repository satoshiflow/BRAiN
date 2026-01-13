/**
 * React Query hooks for Business Factory
 *
 * Template system for business processes, workflows, and automation
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export type ProcessStatus = 'draft' | 'active' | 'deprecated';
export type TriggerType = 'manual' | 'scheduled' | 'event' | 'api';
export type ActionType = 'mission' | 'notification' | 'integration' | 'script';

export interface ProcessStep {
  id: string;
  name: string;
  type: ActionType;
  order: number;
  config: Record<string, unknown>;
  retry_policy?: {
    max_retries: number;
    retry_delay_ms: number;
  };
  conditions?: Record<string, unknown>;
  on_success?: string; // Next step ID
  on_failure?: string; // Fallback step ID
}

export interface ProcessTrigger {
  id: string;
  type: TriggerType;
  config: Record<string, unknown>;
  enabled: boolean;
}

export interface BusinessProcess {
  id: string;
  name: string;
  description: string;
  category: string;
  status: ProcessStatus;
  triggers: ProcessTrigger[];
  steps: ProcessStep[];
  variables?: Record<string, unknown>;
  tags?: string[];
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  execution_count?: number;
  success_rate?: number;
}

export interface ProcessStats {
  total_processes: number;
  active: number;
  draft: number;
  deprecated: number;
  processes_by_category: Record<string, number>;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_success_rate?: number;
  total_steps: number;
}

export interface CreateProcessRequest {
  name: string;
  description: string;
  category: string;
  status?: ProcessStatus;
  triggers?: ProcessTrigger[];
  steps?: ProcessStep[];
  variables?: Record<string, unknown>;
  tags?: string[];
}

export interface UpdateProcessRequest {
  name?: string;
  description?: string;
  category?: string;
  status?: ProcessStatus;
  triggers?: ProcessTrigger[];
  steps?: ProcessStep[];
  variables?: Record<string, unknown>;
  tags?: string[];
}

export interface ExecuteProcessRequest {
  process_id: string;
  input_variables?: Record<string, unknown>;
  trigger_type?: TriggerType;
}

export interface ExecuteProcessResponse {
  execution_id: string;
  process_id: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface ProcessExecution {
  id: string;
  process_id: string;
  process_name: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  steps_completed: number;
  steps_total: number;
  result?: Record<string, unknown>;
  error?: string;
}

// ============================================================================
// API Functions (Placeholder - will be implemented when backend is ready)
// ============================================================================

async function fetchProcessStats(): Promise<ProcessStats> {
  // TODO: Implement when backend endpoint is ready
  // For now, return mock data
  return {
    total_processes: 18,
    active: 12,
    draft: 5,
    deprecated: 1,
    processes_by_category: {
      'Sales': 5,
      'Support': 4,
      'Operations': 3,
      'Marketing': 3,
      'Finance': 3,
    },
    total_executions: 2847,
    successful_executions: 2653,
    failed_executions: 194,
    average_success_rate: 93.2,
    total_steps: 89,
  };
}

async function fetchBusinessProcesses(): Promise<BusinessProcess[]> {
  // TODO: Implement when backend endpoint is ready
  return [];
}

async function fetchBusinessProcess(id: string): Promise<BusinessProcess> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function createBusinessProcess(request: CreateProcessRequest): Promise<BusinessProcess> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function updateBusinessProcess(id: string, request: UpdateProcessRequest): Promise<BusinessProcess> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function deleteBusinessProcess(id: string): Promise<void> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function duplicateBusinessProcess(id: string, newName: string): Promise<BusinessProcess> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function executeBusinessProcess(request: ExecuteProcessRequest): Promise<ExecuteProcessResponse> {
  // TODO: Implement when backend endpoint is ready
  throw new Error('Not implemented');
}

async function fetchProcessExecutions(processId?: string): Promise<ProcessExecution[]> {
  // TODO: Implement when backend endpoint is ready
  return [];
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get business factory statistics
 */
export function useProcessStats() {
  return useQuery<ProcessStats>({
    queryKey: ['business', 'stats'],
    queryFn: fetchProcessStats,
    refetchInterval: 60_000, // Refresh every minute
    staleTime: 30_000,
    retry: 2,
  });
}

/**
 * Get all business processes
 */
export function useBusinessProcesses() {
  return useQuery<BusinessProcess[]>({
    queryKey: ['business', 'processes'],
    queryFn: fetchBusinessProcesses,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Get single business process by ID
 */
export function useBusinessProcess(id: string) {
  return useQuery<BusinessProcess>({
    queryKey: ['business', 'processes', id],
    queryFn: () => fetchBusinessProcess(id),
    enabled: !!id,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Get process executions
 */
export function useProcessExecutions(processId?: string) {
  return useQuery<ProcessExecution[]>({
    queryKey: processId ? ['business', 'executions', processId] : ['business', 'executions'],
    queryFn: () => fetchProcessExecutions(processId),
    refetchInterval: 15_000, // Refresh every 15 seconds
    staleTime: 10_000,
    retry: 2,
  });
}

/**
 * Create new business process
 */
export function useCreateBusinessProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBusinessProcess,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business', 'processes'] });
      queryClient.invalidateQueries({ queryKey: ['business', 'stats'] });
    },
  });
}

/**
 * Update business process
 */
export function useUpdateBusinessProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: UpdateProcessRequest }) =>
      updateBusinessProcess(id, request),
    onSuccess: (data) => {
      queryClient.setQueryData(['business', 'processes', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['business', 'processes'] });
      queryClient.invalidateQueries({ queryKey: ['business', 'stats'] });
    },
  });
}

/**
 * Delete business process
 */
export function useDeleteBusinessProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteBusinessProcess,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business', 'processes'] });
      queryClient.invalidateQueries({ queryKey: ['business', 'stats'] });
    },
  });
}

/**
 * Duplicate business process
 */
export function useDuplicateBusinessProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, newName }: { id: string; newName: string }) =>
      duplicateBusinessProcess(id, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business', 'processes'] });
      queryClient.invalidateQueries({ queryKey: ['business', 'stats'] });
    },
  });
}

/**
 * Execute business process
 */
export function useExecuteBusinessProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: executeBusinessProcess,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business', 'executions'] });
      queryClient.invalidateQueries({ queryKey: ['business', 'stats'] });
    },
  });
}

/**
 * Helper hook: Get processes by category
 */
export function useBusinessProcessesByCategory(category?: string) {
  const { data: processes } = useBusinessProcesses();

  if (!category || !processes) return processes ?? [];

  return processes.filter((p) => p.category === category);
}

/**
 * Helper hook: Get processes by status
 */
export function useBusinessProcessesByStatus(status?: ProcessStatus) {
  const { data: processes } = useBusinessProcesses();

  if (!status || !processes) return processes ?? [];

  return processes.filter((p) => p.status === status);
}

/**
 * Helper hook: Search processes
 */
export function useSearchBusinessProcesses(query: string) {
  const { data: processes } = useBusinessProcesses();

  if (!query || !processes) return processes ?? [];

  const lowercaseQuery = query.toLowerCase();
  return processes.filter(
    (p) =>
      p.name.toLowerCase().includes(lowercaseQuery) ||
      p.description.toLowerCase().includes(lowercaseQuery) ||
      p.tags?.some((tag) => tag.toLowerCase().includes(lowercaseQuery))
  );
}

/**
 * Helper hook: Get high-performing processes
 */
export function useHighPerformingProcesses(threshold: number = 90) {
  const { data: processes } = useBusinessProcesses();

  if (!processes) return [];

  return processes.filter(
    (p) => p.success_rate !== undefined && p.success_rate >= threshold
  );
}
