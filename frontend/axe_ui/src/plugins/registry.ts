import type { Plugin, PluginContext, UiSlot, UiSlotRenderer } from "./types";

const PLUGIN_TIMEOUT_MS = 5000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`Plugin operation timed out after ${ms}ms`)), ms),
    ),
  ]);
}

export class PluginRegistry {
  private plugins: Map<string, Plugin> = new Map();
  private uiSlots: Map<UiSlot, Set<UiSlotRenderer>> = new Map();
  private context: PluginContext | null = null;

  register(plugin: Plugin): void {
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
    console.log(`[PluginRegistry] Unregistered plugin: ${pluginId}`);
  }

  get(pluginId: string): Plugin | undefined {
    return this.plugins.get(pluginId);
  }

  getAll(): Plugin[] {
    return Array.from(this.plugins.values());
  }

  getByPermission(permission: string): Plugin[] {
    return this.getAll().filter((p) => p.manifest.permissions.includes(permission as never));
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
      if (plugin.hooks.onMount) {
        try {
          const result = plugin.hooks.onMount({}, this.context!);
          if (result) {
            await withTimeout(Promise.resolve(result) as Promise<unknown>, PLUGIN_TIMEOUT_MS);
          }
        } catch (err) {
          console.error(`[PluginRegistry] ${plugin.manifest.id} onMount failed:`, err);
        }
      }
    });
    await Promise.all(initPromises);
  }

  async destroy(): Promise<void> {
    if (!this.context) return;
    const destroyPromises = Array.from(this.plugins.values()).map(async (plugin) => {
      if (plugin.hooks.onUnmount) {
        try {
          const result = plugin.hooks.onUnmount({}, this.context!);
          if (result) {
            await withTimeout(Promise.resolve(result) as Promise<unknown>, PLUGIN_TIMEOUT_MS);
          }
        } catch (err) {
          console.error(`[PluginRegistry] ${plugin.manifest.id} onUnmount failed:`, err);
        }
      }
    });
    await Promise.all(destroyPromises);
    this.plugins.clear();
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
          const result = plugin.hooks.onCommand({ command, args }, this.context);
          if (result) {
            const awaited = await withTimeout(Promise.resolve(result), PLUGIN_TIMEOUT_MS);
            if (awaited !== undefined) return awaited;
          }
        } catch (err) {
          console.error(`[PluginRegistry] ${plugin.manifest.id} onCommand failed:`, err);
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
}

export const pluginRegistry = new PluginRegistry();

export async function initializePlugins(context: PluginContext): Promise<void> {
  pluginRegistry.setContext(context);
  await pluginRegistry.initialize();
}

export async function destroyPlugins(): Promise<void> {
  await pluginRegistry.destroy();
}
