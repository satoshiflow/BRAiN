/**
 * AXE UI Configuration
 * 
 * Configuration follows Runtime Deployment Contract (docs/specs/runtime_deployment_contract.md)
 * 
 * Priority:
 * 1. Explicit env var (NEXT_PUBLIC_BRAIN_API_BASE, NEXT_PUBLIC_APP_ENV)
 * 2. Auto-detection (hostname-based)
 * 3. Safe default (production)
 */

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

export type RuntimeMode = "local" | "production";

/**
 * Detect runtime mode based on environment markers.
 * 
 * Priority:
 * 1. Explicit NEXT_PUBLIC_APP_ENV
 * 2. Auto-detection (hostname check - browser only)
 * 3. Default: production (safe, fail-closed)
 */
export function detectRuntimeMode(): RuntimeMode {
  // 1. Explicit override
  const explicit = process.env.NEXT_PUBLIC_APP_ENV;
  if (explicit === "local" || explicit === "production") {
    return explicit;
  }
  
  // 2. Auto-detection (browser only)
  if (typeof window !== "undefined") {
    return LOCAL_HOSTS.has(window.location.hostname) ? "local" : "production";
  }
  
  // 3. Default (SSR safe)
  return "production";
}

/**
 * Get API base URL for given runtime mode.
 * 
 * Priority:
 * 1. Explicit override (NEXT_PUBLIC_BRAIN_API_BASE)
 * 2. Mode-based defaults
 */
export function getApiBase(mode?: RuntimeMode): string {
  // Explicit override always wins
  const explicit = process.env.NEXT_PUBLIC_BRAIN_API_BASE;
  if (explicit) {
    return explicit;
  }
  
  // Use provided mode or detect it
  const runtimeMode = mode ?? detectRuntimeMode();
  
  // Mode-based defaults
  if (runtimeMode === "local") {
    return "http://127.0.0.1:8000";
  }
  
  // Remote default
  return "https://api.brain.falklabs.de";
}

/**
 * Get current runtime mode (singleton cached).
 */
export function getRuntimeMode(): RuntimeMode {
  return detectRuntimeMode();
}

/**
 * Centralized configuration object (singleton).
 */
export const config = {
  runtimeMode: detectRuntimeMode(),

  api: {
    base: getApiBase(),
  },

  // LLM Model Configuration
  llm: {
    // Default model for AXE chat
    defaultModel: process.env.NEXT_PUBLIC_AXE_DEFAULT_MODEL || "qwen2.5:0.5b",

    // Available models (can be extended)
    availableModels: [
      { id: "qwen2.5:0.5b", name: "Qwen 2.5 (0.5B)", provider: "ollama" },
      { id: "qwen2.5:1.5b", name: "Qwen 2.5 (1.5B)", provider: "ollama" },
      { id: "qwen2.5:3b", name: "Qwen 2.5 (3B)", provider: "ollama" },
    ],
  },

  // Chat Configuration
  chat: {
    streamResponses: false,
    maxHistoryLength: 50,
  },
};

// Helper to get default LLM model
export const getDefaultModel = () => config.llm.defaultModel;

// Helper to get available models
export const getAvailableModels = () => config.llm.availableModels;
