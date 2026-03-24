/**
 * Embedding Configuration Types and Utilities
 * 
 * Defines the contract for initializing AXE Floating Widget on external sites.
 * See: docs/specs/axe_widget_embedding_contract_v1.md
 */

import type { PluginHook, PluginHookHandler, PluginManifest } from "@/src/plugins/types";

export interface WidgetBranding {
  logoUrl?: string;
  headerTitle?: string;
  primaryColor?: string;
  secondaryColor?: string;
}

export interface WidgetAnalyticsConfig {
  webhookUrl?: string;
  webhookSecret?: string;
  batchSize?: number;
  batchInterval?: number;
}

export interface WidgetFeatureFlags {
  enableUpload?: boolean;
  enableCamera?: boolean;
  enableCanvas?: boolean;
}

export type AXEEmbeddingErrorCode =
  | "ORIGIN_MISMATCH"
  | "CONFIG_INVALID"
  | "BACKEND_UNAVAILABLE"
  | "TRUST_TIER_BLOCKED"
  | "PLUGIN_LOAD_FAILED"
  | "SERVICE_WORKER_FAILED"
  | "UNKNOWN";

export interface AXEEmbeddingError extends Error {
  code: AXEEmbeddingErrorCode;
  message: string;
  details?: Record<string, unknown>;
}

export function createEmbeddingError(
  code: AXEEmbeddingErrorCode,
  message: string,
  details?: Record<string, unknown>
): AXEEmbeddingError {
  const error = new Error(message) as AXEEmbeddingError;
  error.code = code;
  error.details = details;
  return error;
}

export function isEmbeddingError(error: unknown): error is AXEEmbeddingError {
  if (!(error instanceof Error)) {
    return false;
  }

  const candidate = error as Partial<AXEEmbeddingError>;
  return typeof candidate.code === "string";
}

export type WidgetPosition = "bottom-right" | "bottom-left" | "top-right" | "top-left";
export type WidgetTheme = "light" | "dark";

/**
 * Required configuration for FloatingAxe widget initialization
 */
export interface FloatingAxeConfigRequired {
  /** Unique application identifier for origin validation + rate limiting */
  appId: string;

  /** Backend API base URL (e.g., "https://api.brain.example.com") */
  backendUrl: string;

  /** Allowed origins (must include current window.location.origin) */
  originAllowlist: string | string[];
}

/**
 * Optional configuration for FloatingAxe widget
 */
export interface FloatingAxeConfigOptional {
  /** Widget position on screen (default: "bottom-right") */
  position?: WidgetPosition;

  /** Theme variant (default: "light") */
  theme?: WidgetTheme;

  /** Session ID for chat continuity (auto-generated if not provided) */
  sessionId?: string;

  /** Enable debug logging to console (default: false) */
  debug?: boolean;

  /** Plugins to auto-load on widget initialization */
  plugins?: PluginManifest[];

  /** CSS custom properties override */
  customCss?: Record<string, string>;

  /** Optional branding settings for embedded widgets */
  branding?: WidgetBranding;

  /** Optional analytics settings */
  analytics?: WidgetAnalyticsConfig;

  /** Optional webhook endpoint for widget events */
  webhookUrl?: string;

  /** Optional shared secret for HMAC-SHA256 webhook signatures */
  webhookSecret?: string;

  /** Optional feature flags for advanced UI capabilities */
  features?: WidgetFeatureFlags;

  /** Callback when widget initializes successfully */
  onReady?: (widget: FloatingAxeInstance) => void;

  /** Callback when widget encounters an initialization error */
  onError?: (error: AXEEmbeddingError) => void;
}

/**
 * Complete configuration = required + optional
 */
export type FloatingAxeConfig = FloatingAxeConfigRequired & FloatingAxeConfigOptional;

/**
 * Public interface for FloatingAxe widget instance
 */
export interface FloatingAxeInstance {
  /** Initialize the widget (called automatically after construction) */
  initialize(): Promise<void>;

  /** Destroy the widget and clean up resources */
  destroy(): Promise<void>;

  /** Open the widget panel */
  open(): void;

  /** Close the widget panel */
  close(): void;

  /** Check if widget panel is open */
  isOpen(): boolean;

  /** Register a plugin dynamically */
  registerPlugin(
    manifest: PluginManifest,
    hooks?: Partial<Record<PluginHook, PluginHookHandler<unknown, unknown>>>
  ): Promise<void>;

  /** Unregister a plugin */
  unregisterPlugin(pluginId: string): void;

  /** Send a chat message programmatically */
  sendMessage(content: string): Promise<void>;

  /** Clear chat history */
  clearChat(): void;

  /** Get current session ID */
  getSessionId(): string;

  /** Subscribe to widget events */
  on(event: AXEWidgetEvent, callback: (...args: unknown[]) => void): () => void;

  /** Emit a custom event */
  emit(event: string, ...args: unknown[]): void;
}

export type AXEWidgetEvent =
  | "ready"
  | "error"
  | "open"
  | "close"
  | "message-sent"
  | "message-received"
  | "plugin-registered"
  | "plugin-unregistered";

/**
 * Normalize origin allowlist to array of FQDNs
 */
export function normalizeOriginAllowlist(list: string | string[]): string[] {
  const items = Array.isArray(list) ? list : list.split(",");
  return items.map((item) => item.trim()).filter((item) => item.length > 0);
}

/**
 * Validate configuration object
 */
export function validateConfig(config: Partial<FloatingAxeConfig>): { valid: boolean; error?: string } {
  if (!config.appId) {
    return { valid: false, error: "appId is required" };
  }
  if (!config.backendUrl) {
    return { valid: false, error: "backendUrl is required" };
  }
  if (!config.originAllowlist) {
    return { valid: false, error: "originAllowlist is required" };
  }
  if (config.position && !["bottom-right", "bottom-left", "top-right", "top-left"].includes(config.position)) {
    return { valid: false, error: `Invalid position: ${config.position}` };
  }
  if (config.theme && !["light", "dark"].includes(config.theme)) {
    return { valid: false, error: `Invalid theme: ${config.theme}` };
  }
  return { valid: true };
}

/**
 * Validate current window.location.origin against allowlist
 */
export function validateOrigin(allowlist: string[]): { valid: boolean; error?: string } {
  if (typeof window === "undefined") {
    return { valid: false, error: "window is not defined (SSR context)" };
  }

  let currentUrl: URL;
  try {
    currentUrl = new URL(window.location.origin);
  } catch {
    return { valid: false, error: `Invalid current origin: ${window.location.origin}` };
  }

  const isAllowed = allowlist.some((allowed) => {
    const value = allowed.trim();
    if (!value) {
      return false;
    }

    if (value.startsWith("http://") || value.startsWith("https://")) {
      try {
        const url = new URL(value);
        if (url.pathname !== "/" || url.search || url.hash) {
          return false;
        }
        return url.origin === currentUrl.origin;
      } catch {
        return false;
      }
    }

    if (value.includes("/") || value.includes("?") || value.includes("#") || value.includes("*")) {
      return false;
    }

    try {
      const hostUrl = new URL(`https://${value}`);
      const normalizedHost = hostUrl.port ? `${hostUrl.hostname}:${hostUrl.port}` : hostUrl.hostname;
      if (normalizedHost.toLowerCase() !== value.toLowerCase()) {
        return false;
      }

      const hostnameMatches = hostUrl.hostname.toLowerCase() === currentUrl.hostname.toLowerCase();
      const portMatches = hostUrl.port ? hostUrl.port === currentUrl.port : true;
      return hostnameMatches && portMatches;
    } catch {
      return false;
    }
  });

  if (!isAllowed) {
    return {
      valid: false,
      error: `Origin ${currentUrl.origin} not in allowlist: ${allowlist.join(", ")}`,
    };
  }

  return { valid: true };
}

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  return `axe_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Generate a unique request ID
 */
export function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}
