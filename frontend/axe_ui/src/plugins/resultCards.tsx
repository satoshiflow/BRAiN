import type { Plugin } from "./types";
import { pluginRegistry } from "./registry";
import { emitPluginEvent } from "./eventBus";

export interface ResultCard {
  id: string;
  type: "info" | "success" | "warning" | "error" | "code" | "action";
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
  actions?: { label: string; action: string }[];
}

const resultCardsManifest = {
  id: "result-cards",
  version: "1.0.0",
  apiVersion: "v1",
  name: "Result Cards",
  description: "Display structured tool and mission results as rich cards in chat",
  permissions: ["chat:read", "chat:write", "ui:result.cards"] as const,
  uiSlots: ["result.cards"] as const,
};

function ResultCards() {
  return null;
}

const resultCardsPlugin: Plugin = {
  manifest: resultCardsManifest,
  hooks: {
    onMount: async () => {
      pluginRegistry.registerUiSlot("result.cards", ResultCards);
      console.log("[result-cards] Plugin mounted, UI slot registered");
    },
    onUnmount: async () => {
      console.log("[result-cards] Plugin unmounted");
    },
    onResult: async (data) => {
      const ctx = pluginRegistry.getContext();
      if (!ctx) return;
      const result = data as { type: string; title: string; content: string; metadata?: Record<string, unknown> };
      const card: ResultCard = {
        id: `card-${Date.now()}`,
        type: result.type as ResultCard["type"] || "info",
        title: result.title,
        content: result.content,
        metadata: result.metadata,
        actions: result.metadata?.actions as ResultCard["actions"],
      };
      await emitPluginEvent("message.sent", {
        role: "assistant",
        content: JSON.stringify({ __axeCard: card }),
        id: `card-${Date.now()}`,
      }, ctx);
    },
  },
};

export default resultCardsPlugin;
