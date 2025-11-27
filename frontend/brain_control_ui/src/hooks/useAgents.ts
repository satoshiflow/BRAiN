// frontend/brain_control_ui/src/hooks/useAgents.ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export type AgentState = "healthy" | "degraded" | "offline" | "unknown";

export type AgentsInfo = {
  name: string;
  version: string;
  status?: string;
  description?: string;
};

export type AgentStatus = {
  id: string;
  name: string;
  state: AgentState;
  last_heartbeat?: string | null;
  current_mission_id?: string | null;
  capabilities: string[];
  meta: Record<string, string>;
};

export function useAgentsInfo() {
  return useQuery({
    queryKey: ["agents", "info"],
    queryFn: () => apiGet<AgentsInfo>("/api/agents/info"),
  });
}

export function useSupervisorAgents() {
  return useQuery({
    queryKey: ["agents", "list"],
    queryFn: () => apiGet<AgentStatus[]>("/api/supervisor/agents"),
    refetchInterval: 10_000, // alle 10 Sekunden aktualisieren
  });
}
