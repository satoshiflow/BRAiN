// frontend/brain_control_ui/src/hooks/useAgents.ts
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { brainApi, type AgentsInfo } from "@/lib/brainApi";
import { api } from "@/lib/api";

/**
 * Agentenstatus wie sie vom Lifecycle- oder Supervisor-System gemeldet werden.
 * Das Interface ist bewusst generisch gehalten, damit wir verschiedene
 * Backend-Varianten (Supervisor, Lifecycle-Modul) abbilden können.
 */
export interface AgentStatus {
  id: string;
  name?: string;
  role?: string;
  state?: string;
  status?: string; // alternative Bezeichnung
  capabilities?: string[];
  last_heartbeat?: string;
  current_mission_id?: string | null;
  generation?: number;
  meta?: Record<string, any>;
}

/**
 * Payloads für das Agent Lifecycle API (Register / Heartbeat / Deregister).
 * Werden vom Lifecycle-Deck verwendet.
 */
export interface AgentRegisterPayload {
  agent_id: string;
  name?: string;
  role?: string;
  capabilities?: string[];
  meta?: Record<string, any>;
}

export interface AgentHeartbeatPayload {
  agent_id: string;
  status?: string;
  current_mission_id?: string | null;
  meta?: Record<string, any>;
}

export interface AgentDeregisterPayload {
  agent_id: string;
  reason?: string;
}

/* ------------------------------------------------------------------
   READ HOOKS – Info + Supervisor Agents
-------------------------------------------------------------------*/

/**
 * Basisinformationen zum Agents-System
 * GET /api/agents/info
 */
export function useAgentsInfo() {
  return useQuery<AgentsInfo>({
    queryKey: ["agents", "info"],
    queryFn: () => brainApi.agents.info(),
    refetchInterval: 15_000,
  });
}

/**
 * Agentenliste wie sie der Supervisor bzw. das Missions-System meldet.
 * Aktuell mappen wir auf:
 * GET /api/missions/agents/info
 */
export function useSupervisorAgents() {
  return useQuery<AgentStatus[]>({
    queryKey: ["supervisor", "agents"],
    queryFn: async () => {
      const raw = await brainApi.missions.agentsInfo();
      // Versuche einige gängige Strukturen zu normalisieren:
      if (Array.isArray(raw)) return raw as AgentStatus[];
      if (Array.isArray((raw as any)?.agents)) {
        return (raw as any).agents as AgentStatus[];
      }
      return [];
    },
    refetchInterval: 10_000,
  });
}

/**
 * Generische Agent-Liste. Fürs Control Center verweisen wir aktuell
 * einfach auf die Supervisor-Agents.
 */
export function useAgentList() {
  return useSupervisorAgents();
}

/* ------------------------------------------------------------------
   MUTATION HOOKS – Lifecycle (Register / Heartbeat / Deregister)
   → nutzt /api/agents/register|heartbeat|deregister
   → Backend darf diese Routen später sauber implementieren
-------------------------------------------------------------------*/

export function useAgentRegister() {
  const qc = useQueryClient();
  return useMutation<AgentStatus, Error, AgentRegisterPayload>({
    mutationKey: ["agents", "register"],
    mutationFn: (payload) =>
      api.post<AgentStatus, AgentRegisterPayload>("/api/agents/register", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supervisor", "agents"] });
      qc.invalidateQueries({ queryKey: ["agents", "info"] });
    },
  });
}

export function useAgentHeartbeat() {
  const qc = useQueryClient();
  return useMutation<AgentStatus, Error, AgentHeartbeatPayload>({
    mutationKey: ["agents", "heartbeat"],
    mutationFn: (payload) =>
      api.post<AgentStatus, AgentHeartbeatPayload>(
        "/api/agents/heartbeat",
        payload,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supervisor", "agents"] });
    },
  });
}

export function useAgentDeregister() {
  const qc = useQueryClient();
  return useMutation<void, Error, AgentDeregisterPayload>({
    mutationKey: ["agents", "deregister"],
    mutationFn: (payload) =>
      api.post<void, AgentDeregisterPayload>("/api/agents/deregister", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supervisor", "agents"] });
      qc.invalidateQueries({ queryKey: ["agents", "info"] });
    },
  });
}

/* ------------------------------------------------------------------
   CONSTITUTIONAL AGENTS HOOKS
   → SupervisorAgent, CoderAgent, OpsAgent, ArchitectAgent, AXEAgent
-------------------------------------------------------------------*/

// ============================================================================
// Types for Constitutional Agents
// ============================================================================

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface SupervisionRequest {
  requesting_agent: string;
  action: string;
  context?: Record<string, any>;
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

export interface CodeGenerationRequest {
  spec: string;
  risk_level?: RiskLevel;
}

export interface OdooModuleRequest {
  name: string;
  purpose: string;
  data_types?: string[];
  models?: string[];
  views?: string[];
}

export interface DeploymentRequest {
  app_name: string;
  version: string;
  environment: "development" | "staging" | "production";
  config?: Record<string, any>;
}

export interface ArchitectureReviewRequest {
  system_name: string;
  architecture_spec: Record<string, any>;
  high_risk_ai?: boolean;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  include_history?: boolean;
}

// ============================================================================
// SupervisorAgent Hooks
// ============================================================================

export function useSupervisor() {
  const queryClient = useQueryClient();

  const superviseAction = useMutation<SupervisionResponse, Error, SupervisionRequest>({
    mutationKey: ["supervisor", "supervise"],
    mutationFn: (request) => api.post("/api/agent-ops/supervisor/supervise", request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supervisor", "metrics"] });
    },
  });

  const getMetrics = useQuery<any>({
    queryKey: ["supervisor", "metrics"],
    queryFn: () => api.get("/api/agent-ops/supervisor/metrics"),
    refetchInterval: 30_000, // Refetch every 30s
  });

  return {
    superviseAction,
    getMetrics,
    isSupervising: superviseAction.isPending,
  };
}

// ============================================================================
// CoderAgent Hooks
// ============================================================================

export function useCoder() {
  const queryClient = useQueryClient();

  const generateCode = useMutation<any, Error, CodeGenerationRequest>({
    mutationKey: ["coder", "generate-code"],
    mutationFn: (request) => api.post("/api/agent-ops/coder/generate-code", request),
  });

  const generateOdooModule = useMutation<any, Error, OdooModuleRequest>({
    mutationKey: ["coder", "generate-odoo"],
    mutationFn: (request) => api.post("/api/agent-ops/coder/generate-odoo-module", request),
  });

  return {
    generateCode,
    generateOdooModule,
    isGenerating: generateCode.isPending || generateOdooModule.isPending,
  };
}

// ============================================================================
// OpsAgent Hooks
// ============================================================================

export function useOps() {
  const queryClient = useQueryClient();

  const deployApplication = useMutation<any, Error, DeploymentRequest>({
    mutationKey: ["ops", "deploy"],
    mutationFn: (request) => api.post("/api/agent-ops/ops/deploy", request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops", "health"] });
    },
  });

  const rollbackDeployment = useMutation<any, Error, {
    app_name: string;
    environment: string;
    backup_id: string;
  }>({
    mutationKey: ["ops", "rollback"],
    mutationFn: (request) => api.post("/api/agent-ops/ops/rollback", request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops", "health"] });
    },
  });

  return {
    deployApplication,
    rollbackDeployment,
    isDeploying: deployApplication.isPending,
    isRollingBack: rollbackDeployment.isPending,
  };
}

// ============================================================================
// ArchitectAgent Hooks
// ============================================================================

export function useArchitect() {
  const reviewArchitecture = useMutation<any, Error, ArchitectureReviewRequest>({
    mutationKey: ["architect", "review"],
    mutationFn: (request) => api.post("/api/agent-ops/architect/review", request),
  });

  const checkCompliance = useMutation<any, Error, Record<string, any>>({
    mutationKey: ["architect", "compliance"],
    mutationFn: (spec) => api.post("/api/agent-ops/architect/compliance-check", spec),
  });

  const assessScalability = useMutation<any, Error, Record<string, any>>({
    mutationKey: ["architect", "scalability"],
    mutationFn: (spec) => api.post("/api/agent-ops/architect/scalability-assessment", spec),
  });

  const auditSecurity = useMutation<any, Error, Record<string, any>>({
    mutationKey: ["architect", "security"],
    mutationFn: (spec) => api.post("/api/agent-ops/architect/security-audit", spec),
  });

  return {
    reviewArchitecture,
    checkCompliance,
    assessScalability,
    auditSecurity,
    isReviewing: reviewArchitecture.isPending,
    isCheckingCompliance: checkCompliance.isPending,
  };
}

// ============================================================================
// AXEAgent Hooks
// ============================================================================

export function useAXE() {
  const queryClient = useQueryClient();

  const chat = useMutation<any, Error, ChatRequest>({
    mutationKey: ["axe", "chat"],
    mutationFn: (request) => api.post("/api/agent-ops/axe/chat", request),
  });

  const getSystemStatus = useQuery<any>({
    queryKey: ["axe", "system-status"],
    queryFn: () => api.get("/api/agent-ops/axe/system-status"),
    refetchInterval: 15_000, // Refetch every 15s
  });

  const clearHistory = useMutation({
    mutationKey: ["axe", "clear-history"],
    mutationFn: () => api.delete("/api/agent-ops/axe/history"),
  });

  return {
    chat,
    getSystemStatus,
    clearHistory,
    isChatting: chat.isPending,
  };
}
