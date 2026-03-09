import type { Plugin, PluginContext } from "./types";
import { pluginRegistry } from "./registry";
import { emitPluginEvent } from "./eventBus";

const slashCommandsManifest = {
  id: "slash-commands",
  version: "1.0.0",
  apiVersion: "v1",
  name: "Slash Commands",
  description: "Enables slash commands like /help, /status, /mission in chat",
  permissions: ["chat:read", "chat:write", "ui:composer.actions"] as const,
  uiSlots: ["composer.actions"] as const,
  commands: [
    { name: "help", description: "Show available commands" },
    { name: "status", description: "Show system status" },
    { name: "mission", description: "Create or view mission" },
    { name: "clear", description: "Clear chat history" },
  ],
};

const COMMAND_RESPONSES: Record<string, (context: PluginContext) => string | Promise<string>> = {
  help: () => `Available commands:
/help - Show this message
/status - Check system status
/mission - Create or view mission
/clear - Clear chat history`,
  status: () => `System Status:
- Backend: Online
- Session: ${Date.now()}
- Plugin System: Active`,
  mission: (ctx) => `Mission Command:
Session: ${ctx.sessionId}
To create a mission, describe what you want to accomplish.`,
  clear: () => "Chat history cleared.",
};

function ComposerActions({ context }: { context: PluginContext }) {
  const handleCommand = async (command: string) => {
    const response = await pluginRegistry.handleCommand(command, {});
    if (response && typeof response === "string") {
      await emitPluginEvent("message.sent", {
        role: "assistant",
        content: response,
        id: `cmd-${Date.now()}`,
      }, context);
    }
  };

  return (
    <div className="flex gap-1">
      {["/help", "/status", "/mission"].map((cmd) => (
        <button
          key={cmd}
          onClick={() => handleCommand(cmd.replace("/", ""))}
          className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
        >
          {cmd}
        </button>
      ))}
    </div>
  );
}

const slashCommandsPlugin: Plugin = {
  manifest: slashCommandsManifest,
  hooks: {
    onMount: async () => {
      pluginRegistry.registerUiSlot("composer.actions", ComposerActions);
      console.log("[slash-commands] Plugin mounted, UI slot registered");
    },
    onUnmount: async () => {
      console.log("[slash-commands] Plugin unmounted");
    },
    onCommand: async (data, context) => {
      const { command } = data as { command: string; args: unknown };
      const handler = COMMAND_RESPONSES[command];
      if (handler) {
        const response = await handler(context);
        await emitPluginEvent("message.sent", {
          role: "assistant",
          content: response,
          id: `cmd-${Date.now()}`,
        }, context);
        return response;
      }
      return null;
    },
  },
};

export default slashCommandsPlugin;
