/**
 * React Query hooks for Human-in-the-Loop (HITL) approval system
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ============================================================================
// Types
// ============================================================================

export type ApprovalStatus = "pending" | "approved" | "denied" | "expired";

export interface HITLApprovalRequest {
  token: string;
  approved: boolean;
  approved_by: string;
  reason?: string;
}

export interface HITLApprovalDetails {
  id: number;
  token: string;
  audit_id: string;
  status: ApprovalStatus;

  // Original request
  requesting_agent: string;
  action: string;
  risk_level: string;
  context: Record<string, unknown>;

  // Approval info
  approved_by?: string;
  approval_timestamp?: string;
  approval_reason?: string;

  // Metadata
  created_at: string;
  expires_at?: string;

  // Computed
  is_expired: boolean;
  time_remaining?: number; // seconds
}

export interface HITLQueueResponse {
  total: number;
  pending: HITLApprovalDetails[];
  expired: number;
}

export interface HITLHistoryResponse {
  total: number;
  approvals: HITLApprovalDetails[];
}

export interface HITLStatsResponse {
  total_requests: number;
  pending: number;
  approved: number;
  denied: number;
  expired: number;
  avg_approval_time_seconds?: number;
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Get pending HITL approvals queue
 */
export function useHITLQueue() {
  return useQuery<HITLQueueResponse>({
    queryKey: ["hitl", "queue"],
    queryFn: () => api.get<HITLQueueResponse>("/api/hitl/queue"),
    refetchInterval: 5_000, // Refetch every 5 seconds for real-time updates
  });
}

/**
 * Get HITL approval by token
 */
export function useHITLByToken(token: string | null) {
  return useQuery<HITLApprovalDetails>({
    queryKey: ["hitl", "token", token],
    queryFn: () => api.get<HITLApprovalDetails>(`/api/hitl/token/${token}`),
    enabled: !!token, // Only run query if token is provided
    refetchInterval: 3_000,
  });
}

/**
 * Get HITL approval history
 */
export function useHITLHistory(limit = 50, status?: ApprovalStatus) {
  return useQuery<HITLHistoryResponse>({
    queryKey: ["hitl", "history", limit, status],
    queryFn: () => {
      const params = new URLSearchParams({ limit: limit.toString() });
      if (status) {
        params.append("status", status);
      }
      return api.get<HITLHistoryResponse>(`/api/hitl/history?${params.toString()}`);
    },
    refetchInterval: 30_000, // Refetch every 30 seconds
  });
}

/**
 * Get HITL statistics
 */
export function useHITLStats() {
  return useQuery<HITLStatsResponse>({
    queryKey: ["hitl", "stats"],
    queryFn: () => api.get<HITLStatsResponse>("/api/hitl/stats"),
    refetchInterval: 10_000, // Refetch every 10 seconds
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Approve or deny a HITL request
 */
export function useHITLApprove() {
  const queryClient = useQueryClient();

  return useMutation<HITLApprovalDetails, Error, HITLApprovalRequest>({
    mutationKey: ["hitl", "approve"],
    mutationFn: (request: HITLApprovalRequest) =>
      api.post<HITLApprovalDetails>("/api/hitl/approve", request),
    onSuccess: () => {
      // Invalidate all HITL queries to refetch
      queryClient.invalidateQueries({ queryKey: ["hitl"] });
      // Also invalidate supervisor metrics (HITL affects pending approvals count)
      queryClient.invalidateQueries({ queryKey: ["supervisor", "metrics"] });
    },
  });
}

/**
 * Delete a HITL request (admin only)
 */
export function useHITLDelete() {
  const queryClient = useQueryClient();

  return useMutation<{ message: string }, Error, string>({
    mutationKey: ["hitl", "delete"],
    mutationFn: (token: string) =>
      api.delete<{ message: string }>(`/api/hitl/token/${token}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hitl"] });
    },
  });
}
