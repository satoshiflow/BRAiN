/**
 * AXE UI Configuration
 *
 * MUST HAVE:
 * - Never hardcode real deployment URLs in app feature code.
 * - All runtime service resolution must go through this file.
 * - Prefer explicit env vars or origin-relative path mapping.
 * - The hardcoded host values below are last-resort compatibility fallbacks only.
 *
 * Configuration follows Runtime Deployment Contract
 * (docs/specs/runtime_deployment_contract.md)
 */

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

export type RuntimeMode = "local" | "production";

function normalizeAbsoluteUrl(value?: string): string | null {
  if (!value) {
    return null;
  }

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function resolveOriginRelativeBase(pathValue?: string): string | null {
  if (!pathValue || typeof window === "undefined") {
    return null;
  }

  const normalizedPath = pathValue.startsWith("/") ? pathValue : `/${pathValue}`;
  return `${window.location.origin}${normalizedPath}`;
}

function warnOnCompatibilityFallback(target: "api" | "controlDeck", fallback: string) {
  if (typeof window === "undefined") {
    return;
  }

  if (process.env.NODE_ENV === "production") {
    console.warn(
      `[AXE config] Using compatibility fallback for ${target}: ${fallback}. ` +
        "Set explicit NEXT_PUBLIC_* runtime variables to avoid environment drift."
    );
  }
}

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
  const explicit = normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_BRAIN_API_BASE);
  if (explicit) {
    return explicit;
  }

  const runtimeMode = mode ?? detectRuntimeMode();

  const originRelative = resolveOriginRelativeBase(process.env.NEXT_PUBLIC_BRAIN_API_PATH);
  if (originRelative) {
    return originRelative;
  }

  const modeSpecific =
    runtimeMode === "local"
      ? normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_BRAIN_API_BASE_LOCAL)
      : normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_BRAIN_API_BASE_PRODUCTION);
  if (modeSpecific) {
    return modeSpecific;
  }

  if (runtimeMode === "local") {
    const fallback = "http://127.0.0.1:8000";
    warnOnCompatibilityFallback("api", fallback);
    return fallback;
  }

  const fallback = "https://api.brain.falklabs.de";
  warnOnCompatibilityFallback("api", fallback);
  return fallback;
}

export function getControlDeckBase(mode?: RuntimeMode): string {
  const explicit = normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_CONTROL_DECK_BASE);
  if (explicit) {
    return explicit;
  }

  const runtimeMode = mode ?? detectRuntimeMode();
  const originRelative = resolveOriginRelativeBase(process.env.NEXT_PUBLIC_CONTROL_DECK_PATH);
  if (originRelative) {
    return originRelative;
  }

  const modeSpecific =
    runtimeMode === "local"
      ? normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_CONTROL_DECK_BASE_LOCAL)
      : normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_CONTROL_DECK_BASE_PRODUCTION);
  if (modeSpecific) {
    return modeSpecific;
  }

  if (runtimeMode === "local") {
    const fallback = "http://127.0.0.1:3000";
    warnOnCompatibilityFallback("controlDeck", fallback);
    return fallback;
  }

  const fallback = "https://control.brain.falklabs.de";
  warnOnCompatibilityFallback("controlDeck", fallback);
  return fallback;
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
