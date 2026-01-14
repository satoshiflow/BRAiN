/**
 * React Query hooks for DNA Module
 *
 * Agent genetic optimization system with mutation and evolution tracking
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export interface AgentDNASnapshot {
  agent_id: string;
  snapshot_id: string;
  timestamp: string;
  generation: number;
  params: Record<string, unknown>;
  fitness_score?: number;
  parent_snapshot_id?: string;
  mutation_applied?: string;
}

export interface DNAHistoryResponse {
  agent_id: string;
  snapshots: AgentDNASnapshot[];
  total_snapshots: number;
  current_generation: number;
}

export interface CreateSnapshotRequest {
  agent_id: string;
  params: Record<string, unknown>;
  fitness_score?: number;
}

export interface MutateAgentRequest {
  mutation_rate?: number;
  mutation_strategy?: 'random' | 'gradient' | 'crossover';
}

export interface MutateAgentResponse extends AgentDNASnapshot {
  mutation_details: {
    parameters_changed: string[];
    delta_values: Record<string, number>;
  };
}

// ============================================================================
// API Functions
// ============================================================================

async function createSnapshot(request: CreateSnapshotRequest): Promise<AgentDNASnapshot> {
  const response = await fetch(`${API_BASE}/api/dna/snapshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to create snapshot: ${response.statusText}`);
  return response.json();
}

async function mutateAgent(agentId: string, request: MutateAgentRequest): Promise<MutateAgentResponse> {
  const response = await fetch(`${API_BASE}/api/dna/agents/${agentId}/mutate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to mutate agent: ${response.statusText}`);
  return response.json();
}

async function fetchAgentHistory(agentId: string): Promise<DNAHistoryResponse> {
  const response = await fetch(`${API_BASE}/api/dna/agents/${agentId}/history`);
  if (!response.ok) throw new Error(`Failed to fetch agent history: ${response.statusText}`);
  return response.json();
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get agent DNA evolution history
 */
export function useAgentDNAHistory(agentId: string | undefined) {
  return useQuery<DNAHistoryResponse>({
    queryKey: ['dna', 'history', agentId],
    queryFn: () => fetchAgentHistory(agentId!),
    enabled: !!agentId,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Create DNA snapshot for agent
 */
export function useCreateSnapshot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSnapshot,
    onSuccess: (data) => {
      // Invalidate history for this agent
      queryClient.invalidateQueries({ queryKey: ['dna', 'history', data.agent_id] });
    },
  });
}

/**
 * Mutate agent parameters
 */
export function useMutateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, request }: { agentId: string; request: MutateAgentRequest }) =>
      mutateAgent(agentId, request),
    onSuccess: (data) => {
      // Invalidate history for this agent
      queryClient.invalidateQueries({ queryKey: ['dna', 'history', data.agent_id] });
    },
  });
}

/**
 * Helper hook: Get latest snapshot for agent
 */
export function useLatestSnapshot(agentId: string | undefined) {
  const { data: history } = useAgentDNAHistory(agentId);

  if (!history || history.snapshots.length === 0) return null;

  return history.snapshots[history.snapshots.length - 1];
}

/**
 * Helper hook: Calculate fitness progression
 */
export function useFitnessProgression(agentId: string | undefined) {
  const { data: history } = useAgentDNAHistory(agentId);

  if (!history) return [];

  return history.snapshots
    .filter((s) => s.fitness_score !== undefined)
    .map((s) => ({
      generation: s.generation,
      fitness: s.fitness_score!,
      timestamp: s.timestamp,
    }));
}
