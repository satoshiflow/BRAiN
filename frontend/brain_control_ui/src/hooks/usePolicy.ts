/**
 * React Query hooks for Policy Engine management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ============================================================================
// Types
// ============================================================================

export type PolicyEffect = "allow" | "deny" | "warn" | "audit";
export type PolicyConditionOperator = "==" | "!=" | ">" | "<" | "contains" | "matches" | "in";

export interface PolicyCondition {
  field: string;
  operator: PolicyConditionOperator;
  value: unknown;
}

export interface PolicyRule {
  rule_id: string;
  name: string;
  description?: string;
  effect: PolicyEffect;
  conditions: PolicyCondition[];
  priority: number;
  enabled: boolean;
  metadata?: Record<string, unknown>;
}

export interface Policy {
  policy_id: string;
  name: string;
  version: string;
  description: string;
  rules: PolicyRule[];
  default_effect: PolicyEffect;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  metadata?: Record<string, unknown>;
}

export interface PolicyCreateRequest {
  name: string;
  version?: string;
  description?: string;
  rules?: PolicyRule[];
  default_effect?: PolicyEffect;
  enabled?: boolean;
}

export interface PolicyUpdateRequest {
  name?: string;
  description?: string;
  rules?: PolicyRule[];
  default_effect?: PolicyEffect;
  enabled?: boolean;
}

export interface PolicyListResponse {
  total: number;
  policies: Policy[];
}

export interface PolicyStats {
  total_policies: number;
  active_policies: number;
  total_rules: number;
  total_evaluations: number;
  total_allows: number;
  total_denies: number;
  total_warnings: number;
}

export interface PolicyEvaluationContext {
  agent_id: string;
  agent_role?: string;
  action: string;
  resource?: string;
  environment?: Record<string, unknown>;
  params?: Record<string, unknown>;
}

export interface PolicyEvaluationResult {
  allowed: boolean;
  effect: PolicyEffect;
  matched_rule?: string;
  matched_policy?: string;
  reason: string;
  warnings?: string[];
  requires_audit?: boolean;
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * List all policies
 */
export function usePolicies() {
  return useQuery<PolicyListResponse>({
    queryKey: ["policy", "policies"],
    queryFn: () => api.get<PolicyListResponse>("/api/policy/policies"),
    refetchInterval: 30_000, // Refetch every 30 seconds
  });
}

/**
 * Get specific policy by ID
 */
export function usePolicy(policyId: string | null) {
  return useQuery<Policy>({
    queryKey: ["policy", "policies", policyId],
    queryFn: () => api.get<Policy>(`/api/policy/policies/${policyId}`),
    enabled: !!policyId,
  });
}

/**
 * Get policy statistics
 */
export function usePolicyStats() {
  return useQuery<PolicyStats>({
    queryKey: ["policy", "stats"],
    queryFn: () => api.get<PolicyStats>("/api/policy/stats"),
    refetchInterval: 10_000, // Refetch every 10 seconds
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new policy
 */
export function usePolicyCreate() {
  const queryClient = useQueryClient();

  return useMutation<Policy, Error, PolicyCreateRequest>({
    mutationKey: ["policy", "create"],
    mutationFn: (request: PolicyCreateRequest) =>
      api.post<Policy>("/api/policy/policies", request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy"] });
    },
  });
}

/**
 * Update an existing policy
 */
export function usePolicyUpdate() {
  const queryClient = useQueryClient();

  return useMutation<Policy, Error, { policyId: string; request: PolicyUpdateRequest }>({
    mutationKey: ["policy", "update"],
    mutationFn: ({ policyId, request }) =>
      api.put<Policy>(`/api/policy/policies/${policyId}`, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy"] });
    },
  });
}

/**
 * Delete a policy
 */
export function usePolicyDelete() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationKey: ["policy", "delete"],
    mutationFn: (policyId: string) =>
      api.delete<void>(`/api/policy/policies/${policyId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy"] });
    },
  });
}

/**
 * Test policy rule evaluation (doesn't enforce, just returns result)
 */
export function usePolicyTest() {
  return useMutation<PolicyEvaluationResult, Error, PolicyEvaluationContext>({
    mutationKey: ["policy", "test"],
    mutationFn: (context: PolicyEvaluationContext) =>
      api.post<PolicyEvaluationResult>("/api/policy/test-rule", context),
  });
}

/**
 * Evaluate policy (enforces decision)
 */
export function usePolicyEvaluate() {
  return useMutation<PolicyEvaluationResult, Error, PolicyEvaluationContext>({
    mutationKey: ["policy", "evaluate"],
    mutationFn: (context: PolicyEvaluationContext) =>
      api.post<PolicyEvaluationResult>("/api/policy/evaluate", context),
  });
}
