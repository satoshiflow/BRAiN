/**
 * React Query hooks for Policy Engine
 *
 * Rule-based governance system for agent permissions and action authorization
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from "@/lib/api";


// ============================================================================
// Types
// ============================================================================

export type PolicyEffect = 'allow' | 'deny' | 'warn' | 'audit';

export interface PolicyRule {
  id: string;
  name: string;
  description: string;
  effect: PolicyEffect;
  priority: number;
  conditions: Record<string, unknown>;
  enabled: boolean;
}

export interface EvaluateRequest {
  agent_id: string;
  action: string;
  context: Record<string, unknown>;
}

export interface EvaluateResponse {
  effect: PolicyEffect;
  reason: string;
  matched_rule?: string;
}

export interface TestRuleRequest {
  rule: Omit<PolicyRule, 'id'>;
  test_context: Record<string, unknown>;
}

export interface PolicyStats {
  total_policies: number;
  enabled_policies: number;
  disabled_policies: number;
  policies_by_effect: Record<PolicyEffect, number>;
  total_evaluations: number;
  evaluations_by_effect: Record<PolicyEffect, number>;
}

export interface CreatePolicyRequest {
  name: string;
  description: string;
  effect: PolicyEffect;
  priority?: number;
  conditions: Record<string, unknown>;
  enabled?: boolean;
}

export interface UpdatePolicyRequest {
  name?: string;
  description?: string;
  effect?: PolicyEffect;
  priority?: number;
  conditions?: Record<string, unknown>;
  enabled?: boolean;
}

// ============================================================================
// API Functions
// ============================================================================

async function evaluatePolicy(request: EvaluateRequest): Promise<EvaluateResponse> {
  const response = await fetch(`${API_BASE}/api/policy/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Policy evaluation failed: ${response.statusText}`);
  return response.json();
}

async function testRule(request: TestRuleRequest): Promise<EvaluateResponse> {
  const response = await fetch(`${API_BASE}/api/policy/test-rule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Rule test failed: ${response.statusText}`);
  return response.json();
}

async function fetchPolicyStats(): Promise<PolicyStats> {
  const response = await fetch(`${API_BASE}/api/policy/stats`);
  if (!response.ok) throw new Error(`Failed to fetch policy stats: ${response.statusText}`);
  return response.json();
}

async function fetchPolicies(): Promise<PolicyRule[]> {
  const response = await fetch(`${API_BASE}/api/policy/policies`);
  if (!response.ok) throw new Error(`Failed to fetch policies: ${response.statusText}`);
  return response.json();
}

async function fetchPolicy(id: string): Promise<PolicyRule> {
  const response = await fetch(`${API_BASE}/api/policy/policies/${id}`);
  if (!response.ok) throw new Error(`Failed to fetch policy: ${response.statusText}`);
  return response.json();
}

async function createPolicy(request: CreatePolicyRequest): Promise<PolicyRule> {
  const response = await fetch(`${API_BASE}/api/policy/policies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to create policy: ${response.statusText}`);
  return response.json();
}

async function updatePolicy(id: string, request: UpdatePolicyRequest): Promise<PolicyRule> {
  const response = await fetch(`${API_BASE}/api/policy/policies/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to update policy: ${response.statusText}`);
  return response.json();
}

async function deletePolicy(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/policy/policies/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`Failed to delete policy: ${response.statusText}`);
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get policy system statistics
 */
export function usePolicyStats() {
  return useQuery<PolicyStats>({
    queryKey: ['policy', 'stats'],
    queryFn: fetchPolicyStats,
    refetchInterval: 30_000, // Refresh every 30 seconds
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Get all policies
 */
export function usePolicies() {
  return useQuery<PolicyRule[]>({
    queryKey: ['policy', 'policies'],
    queryFn: fetchPolicies,
    refetchInterval: 60_000, // Refresh every minute
    staleTime: 30_000,
    retry: 2,
  });
}

/**
 * Get single policy by ID
 */
export function usePolicy(id: string) {
  return useQuery<PolicyRule>({
    queryKey: ['policy', 'policies', id],
    queryFn: () => fetchPolicy(id),
    enabled: !!id,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Evaluate action against policies
 */
export function useEvaluatePolicy() {
  return useMutation({
    mutationFn: evaluatePolicy,
  });
}

/**
 * Test policy rule (no side effects)
 */
export function useTestRule() {
  return useMutation({
    mutationFn: testRule,
  });
}

/**
 * Create new policy
 */
export function useCreatePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPolicy,
    onSuccess: () => {
      // Invalidate policies list and stats
      queryClient.invalidateQueries({ queryKey: ['policy', 'policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', 'stats'] });
    },
  });
}

/**
 * Update existing policy
 */
export function useUpdatePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: UpdatePolicyRequest }) =>
      updatePolicy(id, request),
    onSuccess: (data) => {
      // Update cache for specific policy
      queryClient.setQueryData(['policy', 'policies', data.id], data);
      // Invalidate policies list and stats
      queryClient.invalidateQueries({ queryKey: ['policy', 'policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', 'stats'] });
    },
  });
}

/**
 * Delete policy
 */
export function useDeletePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deletePolicy,
    onSuccess: () => {
      // Invalidate policies list and stats
      queryClient.invalidateQueries({ queryKey: ['policy', 'policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', 'stats'] });
    },
  });
}

/**
 * Helper hook: Get policies by effect
 */
export function usePoliciesByEffect(effect?: PolicyEffect) {
  const { data: policies } = usePolicies();

  if (!effect || !policies) return policies ?? [];

  return policies.filter((p) => p.effect === effect);
}

/**
 * Helper hook: Get enabled/disabled policies
 */
export function usePoliciesByStatus(enabled: boolean) {
  const { data: policies } = usePolicies();

  if (!policies) return [];

  return policies.filter((p) => p.enabled === enabled);
}
