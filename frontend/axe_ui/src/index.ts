/**
 * AXE UI - Main Exports
 * Export all public APIs for the AXE widget
 */

// Main Component
export { FloatingAxe } from './components/FloatingAxe';

// Types
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
  AxeAnonymizationLevel
} from './types';

// Stores (for advanced usage)
export { useAxeStore } from './store/axeStore';
export { useDiffStore } from './store/diffStore';
