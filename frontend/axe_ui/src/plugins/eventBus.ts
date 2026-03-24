import type { PluginContext } from "./types";

type EventCallback<T = unknown> = (data: T, context: PluginContext) => void | Promise<void>;

const EVENT_HANDLER_TIMEOUT_MS = 3000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timeoutId: NodeJS.Timeout | null = null;

  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      timeoutId = setTimeout(() => reject(new Error(`Plugin event handler timed out after ${ms}ms`)), ms);
    }),
  ]).finally(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  });
}

export interface AxeEventMap {
  "message.received": { role: "user" | "assistant"; content: string; id: string };
  "message.sent": { role: "user" | "assistant"; content: string; id: string };
  "tool.started": { toolId: string; input: unknown };
  "tool.completed": { toolId: string; result: unknown };
  "tool.failed": { toolId: string; error: string };
  "diff.proposed": { diffId: string; fileId: string };
  "diff.accepted": { diffId: string };
  "diff.rejected": { diffId: string };
  "session.start": { sessionId: string };
  "session.end": { sessionId: string };
}

class PluginEventBus {
  private listeners: Map<string, Set<EventCallback>> = new Map();

  subscribe<K extends keyof AxeEventMap>(
    event: K,
    callback: EventCallback<AxeEventMap[K]>,
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback as EventCallback);
    return () => {
      this.listeners.get(event)?.delete(callback as EventCallback);
    };
  }

  async emit<K extends keyof AxeEventMap>(
    event: K,
    data: AxeEventMap[K],
    context: PluginContext,
  ): Promise<void> {
    const callbacks = this.listeners.get(event);
    if (!callbacks) return;
    const promises = Array.from(callbacks).map((cb) =>
      withTimeout(Promise.resolve(cb(data, context)), EVENT_HANDLER_TIMEOUT_MS).catch((err) =>
        console.error(`[PluginEventBus] ${event} handler error:`, err),
      )
    );
    await Promise.allSettled(promises);
  }
}

export const pluginEventBus = new PluginEventBus();

export async function emitPluginEvent<K extends keyof AxeEventMap>(
  event: K,
  data: AxeEventMap[K],
  context: PluginContext,
): Promise<void> {
  await pluginEventBus.emit(event, data, context);
}
