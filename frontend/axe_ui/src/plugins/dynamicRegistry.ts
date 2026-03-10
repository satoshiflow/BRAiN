/**
 * Dynamic Plugin Registration for Embedded Widgets
 * 
 * Allows external sites to register plugins after widget initialization.
 * Plugins are validated and loaded into the widget's plugin registry.
 */

import type { Plugin, PluginManifest, PluginHookHandler } from "./types";
import { pluginRegistry } from "./registry";

export interface DynamicPluginOptions {
  manifest: PluginManifest;
  hooks: Record<string, PluginHookHandler>;
  timeout?: number;
}

const PLUGIN_LOAD_TIMEOUT_MS = 10000; // 10 second timeout for plugin loading

/**
 * Validate a plugin manifest
 */
export function validatePluginManifest(manifest: PluginManifest): { valid: boolean; error?: string } {
  if (!manifest.id) {
    return { valid: false, error: "Plugin manifest must have an id" };
  }
  if (!manifest.version) {
    return { valid: false, error: "Plugin manifest must have a version" };
  }
  if (!manifest.apiVersion) {
    return { valid: false, error: "Plugin manifest must have an apiVersion" };
  }
  if (!Array.isArray(manifest.permissions)) {
    return { valid: false, error: "Plugin manifest must have permissions array" };
  }
  return { valid: true };
}

/**
 * Register a plugin dynamically (from external site)
 */
export async function registerDynamicPlugin(options: DynamicPluginOptions): Promise<{ success: boolean; error?: string }> {
  try {
    // Validate manifest
    const validation = validatePluginManifest(options.manifest);
    if (!validation.valid) {
      return { success: false, error: validation.error };
    }

    // Check if plugin already registered
    if (pluginRegistry.get(options.manifest.id)) {
      return { success: false, error: `Plugin ${options.manifest.id} already registered` };
    }

    // Check timeout
    const timeout = options.timeout || PLUGIN_LOAD_TIMEOUT_MS;
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("Plugin load timeout")), timeout)
    );

    // Create plugin object
    const plugin: Plugin = {
      manifest: options.manifest,
      hooks: options.hooks,
    };

    // Register with timeout protection
    await Promise.race([
      Promise.resolve().then(() => {
        pluginRegistry.register(plugin);
      }),
      timeoutPromise,
    ]);

    return { success: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return { success: false, error: `Plugin registration failed: ${message}` };
  }
}

/**
 * Unregister a plugin
 */
export function unregisterDynamicPlugin(pluginId: string): { success: boolean; error?: string } {
  try {
    const plugin = pluginRegistry.get(pluginId);
    if (!plugin) {
      return { success: false, error: `Plugin ${pluginId} not found` };
    }
    pluginRegistry.unregister(pluginId);
    return { success: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return { success: false, error: `Plugin unregistration failed: ${message}` };
  }
}

/**
 * Get list of registered plugins
 */
export function getRegisteredPlugins(): PluginManifest[] {
  return pluginRegistry.getAll().map((p) => p.manifest);
}

/**
 * List plugins by permission
 */
export function getPluginsByPermission(permission: string): PluginManifest[] {
  return pluginRegistry.getByPermission(permission).map((p) => p.manifest);
}
