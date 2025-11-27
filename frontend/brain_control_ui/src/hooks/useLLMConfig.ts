// frontend/brain_control_ui/src/hooks/useLLMConfig.ts
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut, apiPost } from "@/lib/api";

export type LLMConfig = {
  provider: string;
  host: string;
  model: string;
  temperature: number;
  max_tokens: number;
  enabled: boolean;
};

export type LLMConfigUpdate = Partial<LLMConfig>;

export type LLMTestResponse = {
  ok: boolean;
  model: string;
  prompt: string;
  raw_response: any;
};

const CONFIG_KEY = ["llm", "config"] as const;

export function useLLMConfig() {
  return useQuery({
    queryKey: CONFIG_KEY,
    queryFn: () => apiGet<LLMConfig>("/api/llm/config"),
  });
}

export function useUpdateLLMConfig() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (body: LLMConfigUpdate) => apiPut<LLMConfig>("/api/llm/config", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CONFIG_KEY });
    },
  });
}

export function useResetLLMConfig() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: () => apiPost<LLMConfig>("/api/llm/config/reset"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CONFIG_KEY });
    },
  });
}

export function useLLMTest() {
  return useMutation({
    mutationFn: (prompt: string) =>
      apiPost<LLMTestResponse>("/api/debug/llm-ping", { prompt }),
  });
}