import { test, expect } from "@playwright/test";
import { pluginRegistry } from "../src/plugins/registry";
import { registerDynamicPlugin, unregisterDynamicPlugin } from "../src/plugins/dynamicRegistry";
import { validatePluginContract } from "../src/plugins/contract";
import { pluginEventBus } from "../src/plugins/eventBus";

const pluginContext = {
  appId: "test-app",
  sessionId: "test-session",
  backendUrl: "http://127.0.0.1:8000",
  locale: "en",
};

test.describe("Plugin runtime maturity", () => {
  test.afterEach(() => {
    unregisterDynamicPlugin("contract-hook-mismatch");
    unregisterDynamicPlugin("timeout-plugin");
  });

  test("validates ui-slot permission requirements", () => {
    const result = validatePluginContract(
      {
        id: "bad-slot-plugin",
        version: "1.0.0",
        apiVersion: "v1",
        name: "Bad Slot Plugin",
        permissions: ["chat:read"],
        uiSlots: ["composer.actions"],
      },
      {},
    );

    expect(result.valid).toBe(false);
    expect(result.errors.some((error) => error.includes("uiSlot 'composer.actions'"))).toBe(true);
  });

  test("rejects dynamic plugin with hook-permission mismatch", async () => {
    const result = await registerDynamicPlugin({
      manifest: {
        id: "contract-hook-mismatch",
        version: "1.0.0",
        apiVersion: "v1",
        name: "Mismatch Plugin",
        permissions: ["chat:read"],
        uiSlots: [],
        commands: [{ name: "dangerous" }],
      },
      hooks: {
        onCommand: async () => "not-allowed",
      },
    });

    expect(result.success).toBe(false);
    expect(result.error || "").toContain("requires permission 'chat:write'");
  });

  test("times out stuck plugin command handlers and keeps runtime responsive", async () => {
    pluginRegistry.setContext(pluginContext);
    const plugin = {
      manifest: {
        id: "timeout-plugin",
        version: "1.0.0",
        apiVersion: "v1",
        name: "Timeout Plugin",
        permissions: ["chat:write" as const],
        uiSlots: [],
        commands: [{ name: "slow" }],
      },
      hooks: {
        onCommand: async () => {
          return new Promise<string>(() => {
            // Never resolves
          });
        },
      },
    };

    pluginRegistry.register(plugin);

    const startedAt = Date.now();
    const result = await pluginRegistry.handleCommand("slow", {});
    const durationMs = Date.now() - startedAt;

    expect(result).toBeNull();
    expect(durationMs).toBeLessThan(7000);
    expect(pluginRegistry.getAll().some((registered) => registered.manifest.id === "timeout-plugin")).toBe(false);
  });

  test("applies event handler timeout to prevent emit hangs", async () => {
    const unsubscribe = pluginEventBus.subscribe("message.sent", async () => {
      return new Promise<void>(() => {
        // Never resolves
      });
    });

    const startedAt = Date.now();
    await pluginEventBus.emit(
      "message.sent",
      {
        role: "user",
        content: "hello",
        id: "event-1",
      },
      pluginContext,
    );
    const durationMs = Date.now() - startedAt;
    unsubscribe();

    expect(durationMs).toBeLessThan(4500);
  });
});
