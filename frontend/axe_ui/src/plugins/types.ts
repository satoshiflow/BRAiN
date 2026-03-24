import type { JsonObject } from "../types";

export type PluginPermission =
  | "chat:read"
  | "chat:write"
  | "ui:composer.actions"
  | "ui:message.actions"
  | "ui:result.cards"
  | "ui:sidepanel.tabs"
  | "tool:run:search"
  | "tool:run:mission"
  | "tool:run:files"
  | "event:subscribe";

export type UiSlot =
  | "composer.actions"
  | "message.actions"
  | "result.cards"
  | "sidepanel.tabs"
  | "header.actions"
  | "footer.actions";

export interface PluginCommand {
  name: string;
  description?: string;
  schema?: JsonObject;
}

export interface PluginManifest {
  id: string;
  version: string;
  apiVersion: string;
  name: string;
  description?: string;
  permissions: readonly PluginPermission[];
  uiSlots: readonly UiSlot[];
  commands?: PluginCommand[];
  dependencies?: string[];
}

export interface PluginContext {
  appId: string;
  sessionId: string;
  userId?: string;
  backendUrl: string;
  locale: string;
}

export type PluginHook =
  | "onMount"
  | "onUnmount"
  | "onMessage"
  | "onCommand"
  | "onResult"
  | "onError"
  | "onSend";

export type PluginHookHandler<T = unknown, R = unknown> = (
  data: T,
  context: PluginContext,
) => R | void | Promise<R | void>;

export interface Plugin {
  manifest: PluginManifest;
  hooks: Partial<Record<PluginHook, PluginHookHandler<unknown, unknown>>>;
}

export interface UiSlotRendererProps {
  context: PluginContext;
}

export type UiSlotRenderer = React.ComponentType<UiSlotRendererProps>;
