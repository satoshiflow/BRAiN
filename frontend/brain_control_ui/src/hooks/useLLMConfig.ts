import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import brainApi from "@/lib/brainApi";

export interface LLMConfig {
  provider: string;
  model: string;
  host: string;
  temperature: number;
  max_tokens: number;
  enabled: boolean;
}

const DEFAULT_LLM_CONFIG: LLMConfig = {
  provider: "openai",
  model: "phi3",
  host: "",
  temperature: 0.7,
  max_tokens: 4097,
  enabled: true,
};

// ------------------------------------------------------
// GET LLM Config
// ------------------------------------------------------
export function useLLMConfig() {
  return useQuery({
    queryKey: ["llm-config"],
    queryFn: async () => {
      // Aktuell holen wir die Config über den Debug-Pfad.
      // Das Backend kann z.B. folgendes liefern:
      // { ok, model, prompt, raw_response: { config: {...} } }
      const raw = await brainApi.debug.llmPing({ prompt: "get-config" });

      if (!raw || typeof raw !== "object") {
        return DEFAULT_LLM_CONFIG;
      }

      const inner =
        (raw as any).raw_response?.config ??
        (raw as any).config ??
        (raw as any);

      const cfg: LLMConfig = {
        provider:
          typeof inner.provider === "string"
            ? inner.provider
            : DEFAULT_LLM_CONFIG.provider,
        model:
          typeof inner.model === "string"
            ? inner.model
            : DEFAULT_LLM_CONFIG.model,
        host:
          typeof inner.host === "string" ? inner.host : DEFAULT_LLM_CONFIG.host,
        temperature:
          typeof inner.temperature === "number"
            ? inner.temperature
            : DEFAULT_LLM_CONFIG.temperature,
        max_tokens:
          typeof inner.max_tokens === "number"
            ? inner.max_tokens
            : DEFAULT_LLM_CONFIG.max_tokens,
        enabled:
          typeof inner.enabled === "boolean"
            ? inner.enabled
            : DEFAULT_LLM_CONFIG.enabled,
      };

      return cfg;
    },
    refetchInterval: false,
  });
}

// ------------------------------------------------------
// UPDATE LLM Config
// ------------------------------------------------------
export function useUpdateLLMConfig() {
  const qc = useQueryClient();

  return useMutation({
    mutationKey: ["llm-config", "update"],
    mutationFn: async (payload: LLMConfig) => {
      return brainApi.debug.llmPing({
        prompt: "update-config",
        ...payload,
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-config"] }),
  });
}

// ------------------------------------------------------
// RESET LLM Config
// ------------------------------------------------------
export function useResetLLMConfig() {
  const qc = useQueryClient();

  return useMutation({
    mutationKey: ["llm-config", "reset"],
    mutationFn: async () => {
      return brainApi.debug.llmPing({ prompt: "reset-config" });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-config"] }),
  });
}

// ------------------------------------------------------
// TEST / Debug LLM – wichtig: immer JSON-Body { prompt }
// ------------------------------------------------------
export function useLLMTest() {
  return useMutation({
    mutationKey: ["llm-config", "test"],
    mutationFn: (payload: { prompt: string }) =>
      brainApi.debug.llmPing(payload),
  });
}
