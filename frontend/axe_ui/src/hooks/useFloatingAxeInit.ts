/**
 * Hook for initializing FloatingAxe widget in embedded context
 * 
 * Handles:
 * - Config validation (required props, origin check)
 * - Plugin registry initialization scoped to widget
 * - Event bus setup
 * - Error handling and callbacks
 */

import { useEffect, useRef, useCallback, useState } from "react";
import type { FloatingAxeConfig, FloatingAxeInstance, AXEEmbeddingError } from "@/lib/embedConfig";
import {
  validateConfig,
  validateOrigin,
  normalizeOriginAllowlist,
  generateSessionId,
  createEmbeddingError,
} from "@/lib/embedConfig";

interface UseFloatingAxeInitOptions {
  config: FloatingAxeConfig;
  debug?: boolean;
}

interface UseFloatingAxeInitReturn {
  widget: FloatingAxeInstance | null;
  isInitialized: boolean;
  error: AXEEmbeddingError | null;
  initialize: () => Promise<void>;
  destroy: () => Promise<void>;
}

export function useFloatingAxeInit({ config, debug }: UseFloatingAxeInitOptions): UseFloatingAxeInitReturn {
  const [widget, setWidget] = useState<FloatingAxeInstance | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<AXEEmbeddingError | null>(null);
  const initializingRef = useRef(false);

  const log = useCallback(
    (level: string, message: string, data?: unknown) => {
      if (debug || config.debug) {
        const prefix = `[FloatingAxe] [${level}]`;
        console.log(prefix, message, data || "");
      }
    },
    [debug, config.debug]
  );

  const handleError = useCallback(
    (err: AXEEmbeddingError) => {
      log("error", err.message, err.details);
      setError(err);
      config.onError?.(err);
    },
    [config, log]
  );

  const initialize = useCallback(async () => {
    if (initializingRef.current) {
      log("warn", "Widget initialization already in progress");
      return;
    }

    initializingRef.current = true;

    try {
      log("info", "Starting FloatingAxe initialization");

      // Step 1: Validate config
      const configValidation = validateConfig(config);
      if (!configValidation.valid) {
        throw createEmbeddingError("CONFIG_INVALID", configValidation.error || "Invalid config");
      }
      log("debug", "Config validation passed");

      // Step 2: Normalize and validate origin
      const allowlist = normalizeOriginAllowlist(config.originAllowlist);
      const originValidation = validateOrigin(allowlist);
      if (!originValidation.valid) {
        throw createEmbeddingError("ORIGIN_MISMATCH", originValidation.error || "Origin not allowed");
      }
      log("debug", "Origin validation passed", { origin: window.location.origin });

      // Step 3: Create session ID
      const sessionId = config.sessionId || generateSessionId();
      log("debug", "Session ID generated", { sessionId });

      // Step 4: Create widget instance
      // Note: Widget creation deferred to FloatingAxe component
      // This hook just prepares context
      setIsInitialized(true);
      log("info", "FloatingAxe initialization complete");

      // Call onReady callback if provided
      // Widget instance will be passed once component creates it
    } catch (err) {
      const embedError = err instanceof Error
        ? createEmbeddingError(
            err.message.includes("Origin") ? "ORIGIN_MISMATCH" : "CONFIG_INVALID",
            err.message
          )
        : createEmbeddingError("UNKNOWN", "An unknown error occurred during initialization");

      handleError(embedError);
    } finally {
      initializingRef.current = false;
    }
  }, [config, log, handleError]);

  const destroy = useCallback(async () => {
    try {
      log("info", "Destroying FloatingAxe widget");
      // Plugin cleanup will be handled by widget component
      setWidget(null);
      setIsInitialized(false);
    } catch (err) {
      const embedError = createEmbeddingError(
        "UNKNOWN",
        err instanceof Error ? err.message : "Error during destroy"
      );
      handleError(embedError);
    }
  }, [log, handleError]);

  // Auto-initialize on mount
  useEffect(() => {
    initialize();
    return () => {
      // Cleanup on unmount
      destroy();
    };
  }, [initialize, destroy]);

  return {
    widget,
    isInitialized,
    error,
    initialize,
    destroy,
  };
}
