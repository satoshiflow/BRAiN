import type { Plugin, PluginContext, PluginHook, PluginPermission, UiSlot, UiSlotRenderer } from "./types";
import { validatePluginContract } from "./contract";

const PLUGIN_TIMEOUT_MS = 5000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timeoutId: NodeJS.Timeout | null = null;

  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      timeoutId = setTimeout(() => reject(new Error(`Plugin operation timed out after ${ms}ms`)), ms);
    }),
  ]).finally(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  });
}

export class PluginRegistry {
  private plugins: Map<string, Plugin> = new Map();
  private uiSlots: Map<UiSlot, Set<UiSlotRenderer>> = new Map();
  private disabledPlugins: Set<string> = new Set();
  private context: PluginContext | null = null;

  register(plugin: Plugin): void {
    const validation = validatePluginContract(plugin.manifest, plugin.hooks);
    if (!validation.valid) {
      throw new Error(
        `[PluginRegistry] Invalid plugin contract for ${plugin.manifest.id}: ${validation.errors.join("; ")}`
      );
    }

    if (this.plugins.has(plugin.manifest.id)) {
      console.warn(`[PluginRegistry] Plugin ${plugin.manifest.id} already registered, skipping.`);
      return;
    }

    this.plugins.set(plugin.manifest.id, plugin);
    console.log(`[PluginRegistry] Registered plugin: ${plugin.manifest.id} v${plugin.manifest.version}`);

    if (plugin.manifest.uiSlots) {
      for (const slot of plugin.manifest.uiSlots) {
        if (!this.uiSlots.has(slot)) {
          this.uiSlots.set(slot, new Set());
        }
      }
    }
  }

  unregister(pluginId: string): void {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) return;
    this.plugins.delete(pluginId);
    this.disabledPlugins.delete(pluginId);
    console.log(`[PluginRegistry] Unregistered plugin: ${pluginId}`);
  }

  get(pluginId: string): Plugin | undefined {
    return this.plugins.get(pluginId);
  }

  getAll(): Plugin[] {
    return Array.from(this.plugins.values()).filter((plugin) => !this.disabledPlugins.has(plugin.manifest.id));
  }

  getByPermission(permission: PluginPermission): Plugin[] {
    return this.getAll().filter((p) => p.manifest.permissions.includes(permission));
  }

  async initializePlugin(pluginId: string): Promise<void> {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) {
      throw new Error(`[PluginRegistry] Plugin not found: ${pluginId}`);
    }
    await this.executeHook(plugin, "onMount", {});
  }

  setContext(context: PluginContext): void {
    this.context = context;
  }

  getContext(): PluginContext | null {
    return this.context;
  }

  async initialize(): Promise<void> {
    if (!this.context) {
      throw new Error("[PluginRegistry] Context not set");
    }
    const initPromises = Array.from(this.plugins.values()).map(async (plugin) => {
      await this.executeHook(plugin, "onMount", {});
    });
    await Promise.all(initPromises);
  }

  async destroy(): Promise<void> {
    if (!this.context) return;
    const destroyPromises = Array.from(this.plugins.values()).map(async (plugin) => {
      await this.executeHook(plugin, "onUnmount", {});
    });
    await Promise.all(destroyPromises);
    this.plugins.clear();
    this.disabledPlugins.clear();
    this.uiSlots.clear();
  }

  async handleCommand(command: string, args: unknown): Promise<unknown> {
    if (!this.context) throw new Error("[PluginRegistry] Context not set");

    const commandPlugins = this.getAll().filter(
      (p) => p.manifest.commands?.some((c) => c.name === command),
    );

    for (const plugin of commandPlugins) {
      if (plugin.hooks.onCommand) {
        try {
          const awaited = await this.executeHook(plugin, "onCommand", { command, args });
          if (awaited !== undefined && awaited !== null) {
            return awaited;
          }
        } catch (err) {
          console.error(`[PluginRegistry] ${plugin.manifest.id} onCommand execution failed:`, err);
        }
      }
    }
    return null;
  }

  registerUiSlot(slot: UiSlot, renderer: UiSlotRenderer): void {
    if (!this.uiSlots.has(slot)) {
      this.uiSlots.set(slot, new Set());
    }
    this.uiSlots.get(slot)!.add(renderer);
  }

  renderUiSlot(slot: UiSlot): UiSlotRenderer[] {
    return Array.from(this.uiSlots.get(slot) || []);
  }

  private async executeHook(plugin: Plugin, hook: PluginHook, data: unknown): Promise<unknown> {
    if (!this.context || this.disabledPlugins.has(plugin.manifest.id)) {
      return undefined;
    }

    const handler = plugin.hooks[hook];
    if (!handler) {
      return undefined;
    }

    try {
      const result = handler(data, this.context);
      return await withTimeout(Promise.resolve(result), PLUGIN_TIMEOUT_MS);
    } catch (err) {
      this.disabledPlugins.add(plugin.manifest.id);
      console.error(`[PluginRegistry] Disabled plugin ${plugin.manifest.id} after ${hook} failure:`, err);

      const onError = plugin.hooks.onError;
      if (onError && hook !== "onError") {
        try {
          await withTimeout(
            Promise.resolve(
              onError(
                {
                  hook,
                  error: err instanceof Error ? err.message : String(err),
                },
                this.context,
              ),
            ),
            PLUGIN_TIMEOUT_MS,
          );
        } catch (onErrorErr) {
          console.error(`[PluginRegistry] ${plugin.manifest.id} onError handler failed:`, onErrorErr);
        }
      }

      return undefined;
    }
  }
}

export const pluginRegistry = new PluginRegistry();

export async function initializePlugins(context: PluginContext): Promise<void> {
  pluginRegistry.setContext(context);
  await pluginRegistry.initialize();
}

export async function destroyPlugins(): Promise<void> {
  await pluginRegistry.destroy();
}
