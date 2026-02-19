// AXE UI Configuration
// These can be overridden via environment variables

export const config = {
  api: {
    base: process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de",
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
