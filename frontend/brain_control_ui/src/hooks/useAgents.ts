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
