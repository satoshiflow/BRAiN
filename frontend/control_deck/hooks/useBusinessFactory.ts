/**
 * React Query hooks for Business Factory
 *
 * Template system for business processes, workflows, and automation
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from "@/lib/api";


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
// API Functions
// ============================================================================

async function fetchProcessStats(): Promise<ProcessStats> {
  const response = await fetch(`${API_BASE}/api/business/processes`);
  if (!response.ok) {
    throw new Error(`Failed to fetch process stats: ${response.statusText}`);
  }
  const data = await response.json();

  // Calculate stats from processes list
  const processes = data.processes || [];
  const totalExecutions = processes.reduce((sum: number, p: any) => sum + (p.total_executions || 0), 0);
  const successfulExecutions = processes.reduce((sum: number, p: any) => sum + (p.successful_executions || 0), 0);
  const failedExecutions = processes.reduce((sum: number, p: any) => sum + (p.failed_executions || 0), 0);

  const processesByCategory = processes.reduce((acc: Record<string, number>, p: any) => {
    const category = p.category || 'Uncategorized';
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {});

  return {
    total_processes: data.total || 0,
    active: processes.filter((p: any) => p.enabled).length,
    draft: processes.filter((p: any) => !p.enabled).length,
    deprecated: 0,
    processes_by_category: processesByCategory,
    total_executions: totalExecutions,
    successful_executions: successfulExecutions,
    failed_executions: failedExecutions,
    average_success_rate: totalExecutions > 0 ? (successfulExecutions / totalExecutions) * 100 : 0,
    total_steps: processes.reduce((sum: number, p: any) => sum + (p.steps?.length || 0), 0),
  };
}

async function fetchBusinessProcesses(): Promise<BusinessProcess[]> {
  const response = await fetch(`${API_BASE}/api/business/processes`);
  if (!response.ok) {
    throw new Error(`Failed to fetch processes: ${response.statusText}`);
  }
  const data = await response.json();
  return data.processes || [];
}

async function fetchBusinessProcess(id: string): Promise<BusinessProcess> {
  const response = await fetch(`${API_BASE}/api/business/processes/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch process: ${response.statusText}`);
  }
  return await response.json();
}

async function createBusinessProcess(request: CreateProcessRequest): Promise<BusinessProcess> {
  const response = await fetch(`${API_BASE}/api/business/processes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to create process: ${response.statusText}`);
  }
  return await response.json();
}

async function updateBusinessProcess(id: string, request: UpdateProcessRequest): Promise<BusinessProcess> {
  const response = await fetch(`${API_BASE}/api/business/processes/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to update process: ${response.statusText}`);
  }
  return await response.json();
}

async function deleteBusinessProcess(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/business/processes/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete process: ${response.statusText}`);
  }
}

async function duplicateBusinessProcess(id: string, newName: string): Promise<BusinessProcess> {
  // Fetch original process
  const original = await fetchBusinessProcess(id);

  // Create duplicate with new name
  const duplicate: CreateProcessRequest = {
    name: newName,
    description: original.description,
    category: original.category,
    status: 'draft' as ProcessStatus,
    triggers: original.triggers,
    steps: original.steps,
    variables: original.variables,
    tags: original.tags,
  };

  return await createBusinessProcess(duplicate);
}

async function executeBusinessProcess(request: ExecuteProcessRequest): Promise<ExecuteProcessResponse> {
  const response = await fetch(`${API_BASE}/api/business/processes/${request.process_id}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      input_data: request.input_variables,
      triggered_by: 'ui_user',
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to execute process: ${response.statusText}`);
  }
  const execution = await response.json();

  return {
    execution_id: execution.id,
    process_id: execution.process_id,
    status: execution.status === 'pending' ? 'running' : execution.status,
    started_at: execution.created_at,
    completed_at: execution.completed_at,
    result: execution.output_data,
    error: execution.error_message,
  };
}

async function fetchProcessExecutions(processId?: string): Promise<ProcessExecution[]> {
  const url = processId
    ? `${API_BASE}/api/business/processes/${processId}/executions`
    : `${API_BASE}/api/business/executions`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch executions: ${response.statusText}`);
  }
  const data = await response.json();
  const executions = data.executions || [];

  return executions.map((exec: any) => ({
    id: exec.id,
    process_id: exec.process_id,
    process_name: '', // Not returned by backend
    status: exec.status,
    started_at: exec.started_at || exec.created_at,
    completed_at: exec.completed_at,
    duration_ms: exec.duration_seconds ? exec.duration_seconds * 1000 : undefined,
    steps_completed: 0, // Not tracked yet
    steps_total: 0, // Not tracked yet
    result: exec.output_data,
    error: exec.error_message,
  }));
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
