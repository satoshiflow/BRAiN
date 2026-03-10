import type { PluginHook, PluginHookHandler, PluginManifest, PluginPermission, UiSlot } from "./types";

const UI_SLOT_PERMISSION_MAP: Record<UiSlot, PluginPermission> = {
  "composer.actions": "ui:composer.actions",
  "message.actions": "ui:message.actions",
  "result.cards": "ui:result.cards",
  "sidepanel.tabs": "ui:sidepanel.tabs",
  "header.actions": "ui:composer.actions",
  "footer.actions": "ui:composer.actions",
};

const HOOK_PERMISSION_MAP: Partial<Record<PluginHook, PluginPermission>> = {
  onMessage: "chat:read",
  onResult: "chat:read",
  onSend: "chat:write",
  onCommand: "chat:write",
};

const VALID_HOOKS: ReadonlySet<PluginHook> = new Set([
  "onMount",
  "onUnmount",
  "onMessage",
  "onCommand",
  "onResult",
  "onError",
  "onSend",
]);

export interface PluginContractValidationResult {
  valid: boolean;
  errors: string[];
}

export function validatePluginContract(
  manifest: PluginManifest,
  hooks: Partial<Record<PluginHook, PluginHookHandler<unknown, unknown>>>
): PluginContractValidationResult {
  const errors: string[] = [];

  if (!manifest.id?.trim()) {
    errors.push("Plugin manifest must have a non-empty id");
  }
  if (!manifest.version?.trim()) {
    errors.push("Plugin manifest must have a non-empty version");
  }
  if (!manifest.apiVersion?.trim()) {
    errors.push("Plugin manifest must have a non-empty apiVersion");
  }
  if (!manifest.name?.trim()) {
    errors.push("Plugin manifest must have a non-empty name");
  }

  if (!Array.isArray(manifest.permissions)) {
    errors.push("Plugin manifest must have permissions array");
  }
  if (!Array.isArray(manifest.uiSlots)) {
    errors.push("Plugin manifest must have uiSlots array");
  }

  for (const uiSlot of manifest.uiSlots || []) {
    const requiredPermission = UI_SLOT_PERMISSION_MAP[uiSlot];
    if (!requiredPermission) {
      errors.push(`Unsupported uiSlot: ${uiSlot}`);
      continue;
    }
    if (!(manifest.permissions || []).includes(requiredPermission)) {
      errors.push(`uiSlot '${uiSlot}' requires permission '${requiredPermission}'`);
    }
  }

  for (const [hookName, handler] of Object.entries(hooks || {})) {
    if (!VALID_HOOKS.has(hookName as PluginHook)) {
      errors.push(`Unsupported hook: ${hookName}`);
      continue;
    }
    if (typeof handler !== "function") {
      errors.push(`Hook '${hookName}' must be a function`);
      continue;
    }

    const requiredPermission = HOOK_PERMISSION_MAP[hookName as PluginHook];
    if (requiredPermission && !(manifest.permissions || []).includes(requiredPermission)) {
      errors.push(`Hook '${hookName}' requires permission '${requiredPermission}'`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
