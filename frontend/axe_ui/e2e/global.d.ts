/**
 * TypeScript declarations for E2E tests
 */

import type { FloatingAxeInstance } from "@/lib/embedConfig";

declare global {
  interface Window {
    AXEWidget: FloatingAxeInstance & {
      config: Record<string, unknown>;
      sessionId: string;
    };
  }
}

export {};
