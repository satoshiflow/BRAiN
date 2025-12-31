/**
 * React Query hooks for BRAiN Credits System (Event Sourcing).
 *
 * Features:
 * - Agent credit management
 * - Real-time balance updates
 * - Transaction history
 * - System metrics
 *
 * Usage:
 *   const { data: balance } = useAgentBalance("agent_123");
 *   const createAgent = useCreateAgent();
 *   const consumeCredits = useConsumeCredits();
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ============================================================================
// Types
// ============================================================================

export interface AgentBalance {
  agent_id: string;
  balance: number;
}

export interface AllBalances {
  balances: Record<string, number>;
  total_agents: number;
}

export interface LedgerEntry {
  event_id: string;
  timestamp: string;
  entity_id: string;
  entity_type: string;
  amount: number;
  balance_after: number;
  reason: string;
  mission_id: string | null;
}

export interface AgentHistory {
  agent_id: string;
  history: LedgerEntry[];
  total_entries: number;
}

export interface CreditMetrics {
  journal: {
    total_events: number;
    file_size_mb: number;
    idempotency_violations: number;
    file_path: string;
  };
  event_bus: {
    total_published: number;
    total_subscriber_errors: number;
    subscribers_by_type: Record<string, number>;
  };
  replay: {
    total_events: number;
    replay_duration_seconds: number;
    last_replay_timestamp: number;
    integrity_errors_count: number;
  };
}

export interface CreateAgentRequest {
  agent_id: string;
  skill_level: number;
  actor_id?: string;
}

export interface CreateAgentResponse {
  agent_id: string;
  initial_credits: number;
  balance: number;
  skill_level: number;
}

export interface ConsumeCreditsRequest {
  agent_id: string;
  amount: number;
  reason: string;
  mission_id?: string;
  actor_id?: string;
}

export interface ConsumeCreditsResponse {
  agent_id: string;
  amount: number;
  balance_after: number;
  reason: string;
  mission_id: string | null;
}

export interface RefundCreditsRequest {
  agent_id: string;
  amount: number;
  reason: string;
  mission_id?: string;
  actor_id?: string;
}

export interface RefundCreditsResponse {
  agent_id: string;
  amount: number;
  balance_after: number;
  reason: string;
  mission_id: string | null;
}

// ============================================================================
// API Client
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function apiCall<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || response.statusText);
  }

  return response.json();
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Get current balance for agent.
 */
export function useAgentBalance(agentId: string | undefined, options?: { enabled?: boolean }) {
  return useQuery<AgentBalance>({
    queryKey: ["credits", "balance", agentId],
    queryFn: () => apiCall(`/api/credits/balance/${agentId}`),
    enabled: options?.enabled !== false && !!agentId,
    refetchInterval: 10_000, // Refetch every 10s
  });
}

/**
 * Get all agent balances.
 */
export function useAllBalances() {
  return useQuery<AllBalances>({
    queryKey: ["credits", "balances"],
    queryFn: () => apiCall("/api/credits/balances"),
    refetchInterval: 30_000, // Refetch every 30s
  });
}

/**
 * Get transaction history for agent.
 */
export function useAgentHistory(
  agentId: string | undefined,
  limit: number = 10,
  options?: { enabled?: boolean }
) {
  return useQuery<AgentHistory>({
    queryKey: ["credits", "history", agentId, limit],
    queryFn: () => apiCall(`/api/credits/history/${agentId}?limit=${limit}`),
    enabled: options?.enabled !== false && !!agentId,
    refetchInterval: 15_000, // Refetch every 15s
  });
}

/**
 * Get Event Sourcing system metrics.
 */
export function useCreditMetrics() {
  return useQuery<CreditMetrics>({
    queryKey: ["credits", "metrics"],
    queryFn: () => apiCall("/api/credits/metrics"),
    refetchInterval: 60_000, // Refetch every 60s
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create agent with initial credits.
 */
export function useCreateAgent() {
  const queryClient = useQueryClient();

  return useMutation<CreateAgentResponse, Error, CreateAgentRequest>({
    mutationFn: (request) =>
      apiCall("/api/credits/agents", {
        method: "POST",
        body: JSON.stringify(request),
      }),
    onSuccess: (data) => {
      // Invalidate balance queries
      queryClient.invalidateQueries({ queryKey: ["credits", "balance", data.agent_id] });
      queryClient.invalidateQueries({ queryKey: ["credits", "balances"] });
      queryClient.invalidateQueries({ queryKey: ["credits", "history", data.agent_id] });
      queryClient.invalidateQueries({ queryKey: ["credits", "metrics"] });
    },
  });
}

/**
 * Consume credits for agent.
 */
export function useConsumeCredits() {
  const queryClient = useQueryClient();

  return useMutation<ConsumeCreditsResponse, Error, ConsumeCreditsRequest>({
    mutationFn: (request) =>
      apiCall("/api/credits/consume", {
        method: "POST",
        body: JSON.stringify(request),
      }),
    onSuccess: (data) => {
      // Invalidate balance queries
      queryClient.invalidateQueries({ queryKey: ["credits", "balance", data.agent_id] });
      queryClient.invalidateQueries({ queryKey: ["credits", "balances"] });
      queryClient.invalidateQueries({ queryKey: ["credits", "history", data.agent_id] });
      queryClient.invalidateQueries({ queryKey: ["credits", "metrics"] });
    },
  });
}

/**
 * Refund credits to agent.
 */
export function useRefundCredits() {
  const queryClient = useQueryClient();

  return useMutation<RefundCreditsResponse, Error, RefundCreditsRequest>({
    mutationFn: (request) =>
      apiCall("/api/credits/refund", {
        method: "POST",
        body: JSON.stringify(request),
      }),
    onSuccess: (data) => {
      // Invalidate balance queries
      queryClient.invalidateQueries({ queryKey: ["credits", "balance", data.agent_id] });
      queryClient.invalidateQueries({ queryKey: ["credits", "balances"] });
      queryClient.invalidateQueries({ queryKey: ["credits", "history", data.agent_id] });
      queryClient.invalidateQueries({ queryKey: ["credits", "metrics"] });
    },
  });
}
