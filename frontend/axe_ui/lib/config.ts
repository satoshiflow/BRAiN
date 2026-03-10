// AXE UI Configuration
// These can be overridden via environment variables

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function inferApiBase(): string {
  const explicitBase = process.env.NEXT_PUBLIC_BRAIN_API_BASE;
  if (explicitBase) {
    return explicitBase;
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (LOCAL_HOSTS.has(host)) {
      return "http://127.0.0.1:8000";
    }
  }

  return "https://api.brain.falklabs.de";
}

function inferAppEnv(): "local" | "production" {
  const explicitEnv = process.env.NEXT_PUBLIC_APP_ENV;
  if (explicitEnv === "local" || explicitEnv === "production") {
    return explicitEnv;
  }

  if (typeof window !== "undefined") {
    return LOCAL_HOSTS.has(window.location.hostname) ? "local" : "production";
  }

  return "production";
}

export const config = {
  appEnv: inferAppEnv(),

  api: {
    base: inferApiBase(),
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

// Helper to get current API base
export const getApiBase = () => config.api.base;

// Helper to get default LLM model
export const getDefaultModel = () => config.llm.defaultModel;

// Helper to get available models
export const getAvailableModels = () => config.llm.availableModels;
