/**
 * React Query hooks for Constitutional Agents
 *
 * Provides hooks for interacting with DSGVO and EU AI Act compliant agent system:
 * - SupervisorAgent: Constitutional guardian with risk-based supervision
 * - CoderAgent: Secure code generation with DSGVO compliance
 * - OpsAgent: Operations and deployment with rollback
 * - ArchitectAgent: Architecture review and compliance auditing
 * - AXEAgent: Conversational assistant
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface SupervisionRequest {
  requesting_agent: string;
  action: string;
  context: Record<string, unknown>;
  risk_level: RiskLevel;
  reason?: string;
}

export interface SupervisionResponse {
  approved: boolean;
  reason: string;
  human_oversight_required: boolean;
  human_oversight_token?: string;
  audit_id: string;
  timestamp: string;
  policy_violations: string[];
}

export interface SupervisorMetrics {
  total_supervision_requests: number;
  approved_actions: number;
  denied_actions: number;
  human_approvals_pending: number;
  approval_rate: number;
}

export interface CodeGenerationRequest {
  spec: string;
  risk_level?: RiskLevel;
}

export interface OdooModuleRequest {
  name: string;
  purpose: string;
  data_types: string[];
  models?: string[];
  views?: string[];
}

export interface DeploymentRequest {
  app_name: string;
  version: string;
  environment: 'development' | 'staging' | 'production';
  config?: Record<string, unknown>;
}

export interface RollbackRequest {
  app_name: string;
  environment: string;
  backup_id: string;
}

export interface ArchitectureReviewRequest {
  system_name: string;
  architecture_spec: {
    uses_ai: boolean;
    processes_personal_data: boolean;
    data_types?: string[];
    international_transfers: boolean;
    components?: string[];
    uses_social_scoring?: boolean;
    uses_biometric_categorization?: boolean;
    has_consent_mechanism?: boolean;
  };
  high_risk_ai: boolean;
}

export interface ArchitectureReviewResponse {
  compliance_score: number;
  eu_ai_act_compliant: boolean;
  dsgvo_compliant: boolean;
  prohibited_practices_detected: string[];
  recommendations: string[];
  security_issues: string[];
  scalability_rating: string;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, unknown>;
  include_history?: boolean;
}

export interface ChatResponse {
  response: string;
  timestamp: string;
}

export interface AgentInfo {
  id: string;
  name: string;
  role: string;
  capabilities: string[];
}

export interface ConstitutionalAgentsInfo {
  name: string;
  version: string;
  agents: AgentInfo[];
  compliance_frameworks: string[];
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchAgentsInfo(): Promise<ConstitutionalAgentsInfo> {
  const response = await fetch(`${API_BASE}/api/agent-ops/info`);
  if (!response.ok) throw new Error(`Failed to fetch agents info: ${response.statusText}`);
  return response.json();
}

async function superviseAction(request: SupervisionRequest): Promise<SupervisionResponse> {
  const response = await fetch(`${API_BASE}/api/agent-ops/supervisor/supervise`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Supervision failed: ${response.statusText}`);
  return response.json();
}

async function fetchSupervisorMetrics(): Promise<SupervisorMetrics> {
  const response = await fetch(`${API_BASE}/api/agent-ops/supervisor/metrics`);
  if (!response.ok) throw new Error(`Failed to fetch metrics: ${response.statusText}`);
  return response.json();
}

async function generateCode(request: CodeGenerationRequest): Promise<{ code: string; explanation: string }> {
  const response = await fetch(`${API_BASE}/api/agent-ops/coder/generate-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Code generation failed: ${response.statusText}`);
  return response.json();
}

async function generateOdooModule(request: OdooModuleRequest): Promise<{ module_path: string; files: string[] }> {
  const response = await fetch(`${API_BASE}/api/agent-ops/coder/generate-odoo-module`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Odoo module generation failed: ${response.statusText}`);
  return response.json();
}

async function deployApplication(request: DeploymentRequest): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/api/agent-ops/ops/deploy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Deployment failed: ${response.statusText}`);
  return response.json();
}

async function rollbackDeployment(request: RollbackRequest): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/api/agent-ops/ops/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Rollback failed: ${response.statusText}`);
  return response.json();
}

async function reviewArchitecture(request: ArchitectureReviewRequest): Promise<ArchitectureReviewResponse> {
  const response = await fetch(`${API_BASE}/api/agent-ops/architect/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Architecture review failed: ${response.statusText}`);
  return response.json();
}

async function chatWithAXE(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/agent-ops/axe/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Chat failed: ${response.statusText}`);
  return response.json();
}

async function fetchSystemStatus(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/api/agent-ops/axe/system-status`);
  if (!response.ok) throw new Error(`Failed to fetch system status: ${response.statusText}`);
  return response.json();
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get information about all constitutional agents
 */
export function useAgentsInfo() {
  return useQuery<ConstitutionalAgentsInfo>({
    queryKey: ['constitutional', 'agents', 'info'],
    queryFn: fetchAgentsInfo,
    staleTime: 60_000, // 1 minute
    retry: 2,
  });
}

/**
 * Get supervisor metrics (total requests, approval rate, etc.)
 */
export function useSupervisorMetrics() {
  return useQuery<SupervisorMetrics>({
    queryKey: ['constitutional', 'supervisor', 'metrics'],
    queryFn: fetchSupervisorMetrics,
    refetchInterval: 30_000, // Refresh every 30 seconds
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Get system status from AXE agent
 */
export function useSystemStatus() {
  return useQuery({
    queryKey: ['constitutional', 'axe', 'status'],
    queryFn: fetchSystemStatus,
    refetchInterval: 15_000, // Refresh every 15 seconds
    staleTime: 10_000,
    retry: 2,
  });
}

/**
 * Request supervision for an action (SupervisorAgent)
 */
export function useSuperviseAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: superviseAction,
    onSuccess: () => {
      // Invalidate metrics to refresh after new request
      queryClient.invalidateQueries({ queryKey: ['constitutional', 'supervisor', 'metrics'] });
    },
  });
}

/**
 * Generate code (CoderAgent)
 */
export function useGenerateCode() {
  return useMutation({
    mutationFn: generateCode,
  });
}

/**
 * Generate Odoo module (CoderAgent)
 */
export function useGenerateOdooModule() {
  return useMutation({
    mutationFn: generateOdooModule,
  });
}

/**
 * Deploy application (OpsAgent)
 */
export function useDeployApplication() {
  return useMutation({
    mutationFn: deployApplication,
  });
}

/**
 * Rollback deployment (OpsAgent)
 */
export function useRollbackDeployment() {
  return useMutation({
    mutationFn: rollbackDeployment,
  });
}

/**
 * Review architecture (ArchitectAgent)
 */
export function useReviewArchitecture() {
  return useMutation({
    mutationFn: reviewArchitecture,
  });
}

/**
 * Chat with AXE agent
 */
export function useChatWithAXE() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: chatWithAXE,
    onSuccess: () => {
      // Optionally invalidate system status after chat
      queryClient.invalidateQueries({ queryKey: ['constitutional', 'axe', 'status'] });
    },
  });
}
