import type { Plugin, PluginContext } from "./types";
import { pluginRegistry } from "./registry";
import { emitPluginEvent } from "./eventBus";

const mobileActionsManifest = {
  id: "mobile-actions",
  version: "1.0.0",
  apiVersion: "v1",
  name: "Mobile Quick Actions",
  description: "Provides quick action buttons optimized for mobile touch interaction",
  permissions: ["chat:read", "chat:write", "ui:composer.actions"] as const,
  uiSlots: ["composer.actions"] as const,
};

const MOBILE_ACTIONS = [
  { label: "Status", command: "status" },
  { label: "Mission", command: "mission" },
  { label: "Clear", command: "clear" },
];

function MobileActions({ context }: { context: PluginContext }) {
  const handleAction = async (command: string) => {
    const result = await pluginRegistry.handleCommand(command, {});
    if (result && typeof result === "string") {
      await emitPluginEvent("message.sent", {
        role: "assistant",
        content: result,
        id: `mobile-${Date.now()}`,
      }, context);
    }
  };

  if (typeof window !== "undefined" && /Mobi|Android/i.test(navigator.userAgent)) {
    return (
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-2 px-2">
        {MOBILE_ACTIONS.map((action) => (
          <button
            key={action.command}
            onClick={() => handleAction(action.command)}
            className="flex-shrink-0 px-3 py-2 text-sm font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-colors touch-manipulation"
          >
            {action.label}
          </button>
        ))}
      </div>
    );
  }
  return null;
}

const mobileActionsPlugin: Plugin = {
  manifest: mobileActionsManifest,
  hooks: {
    onMount: async () => {
      pluginRegistry.registerUiSlot("composer.actions", MobileActions);
      console.log("[mobile-actions] Plugin mounted, UI slot registered");
    },
    onUnmount: async () => {
      console.log("[mobile-actions] Plugin unmounted");
    },
  },
};

export default mobileActionsPlugin;
