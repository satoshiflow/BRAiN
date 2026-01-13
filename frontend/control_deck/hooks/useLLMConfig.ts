/**
 * React Query hooks for LLM Configuration
 *
 * Runtime LLM configuration with support for multiple providers
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';

export interface LLMConfig {
  provider: string;
  host: string;
  model: string;
  temperature: number;
  max_tokens: number;
  enabled: boolean;
}

async function fetchLLMConfig(): Promise<LLMConfig> {
  const response = await fetch(`${API_BASE}/api/llm/config`);
  if (!response.ok) throw new Error(`Failed to fetch LLM config: ${response.statusText}`);
  return response.json();
}

async function updateLLMConfig(config: Partial<LLMConfig>): Promise<LLMConfig> {
  const response = await fetch(`${API_BASE}/api/llm/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) throw new Error(`Failed to update LLM config: ${response.statusText}`);
  return response.json();
}

async function resetLLMConfig(): Promise<LLMConfig> {
  const response = await fetch(`${API_BASE}/api/llm/config/reset`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to reset LLM config: ${response.statusText}`);
  return response.json();
}

/**
 * Get current LLM configuration
 */
export function useLLMConfig() {
  return useQuery<LLMConfig>({
    queryKey: ['llm', 'config'],
    queryFn: fetchLLMConfig,
    staleTime: 60_000, // 1 minute
    retry: 2,
  });
}

/**
 * Update LLM configuration
 */
export function useUpdateLLMConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateLLMConfig,
    onSuccess: (data) => {
      // Update cache immediately
      queryClient.setQueryData(['llm', 'config'], data);
    },
  });
}

/**
 * Reset LLM configuration to defaults
 */
export function useResetLLMConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetLLMConfig,
    onSuccess: (data) => {
      // Update cache immediately
      queryClient.setQueryData(['llm', 'config'], data);
    },
  });
}
