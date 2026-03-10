/**
 * AXE Widget - NPM Package Export
 * 
 * @axe-ui/widget - Floating chat widget for external website embedding
 * 
 * Usage:
 * 
 * import { FloatingAxe } from '@axe-ui/widget';
 * 
 * const widget = new FloatingAxe({
 *   appId: 'my-app',
 *   backendUrl: 'https://api.example.com',
 *   originAllowlist: ['example.com'],
 * });
 * 
 * widget.initialize();
 */

export { FloatingAxe as default, FloatingAxe } from "@/components/FloatingAxe";
export type {
  FloatingAxeConfig,
  FloatingAxeConfigRequired,
  FloatingAxeConfigOptional,
  FloatingAxeInstance,
  AXEWidgetEvent,
  AXEEmbeddingError,
  AXEEmbeddingErrorCode,
  WidgetPosition,
  WidgetTheme,
} from "@/lib/embedConfig";

export {
  validateConfig,
  validateOrigin,
  normalizeOriginAllowlist,
  generateSessionId,
  generateRequestId,
  createEmbeddingError,
} from "@/lib/embedConfig";

export { useFloatingAxeInit } from "@/src/hooks/useFloatingAxeInit";
