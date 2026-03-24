/**
 * AXE UI - Canonical Public Exports
 */

export { default as FloatingAxe } from "./widget";
export * from "./widget";

// Legacy compatibility types/stores (deprecated)
export type {
  FloatingAxeProps,
  AxeConfig,
  AxeMode,
  AxeTheme,
  AxeWidgetPosition,
  AxeMessage,
  AxeFile,
  AxeDiff,
  AxeEvent,
  AxeTrainingMode,
  AxeAnonymizationLevel,
} from "./types";

export { useAxeStore } from "./store/axeStore";
export { useDiffStore } from "./store/diffStore";
