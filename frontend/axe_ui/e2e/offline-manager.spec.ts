import { test, expect } from "@playwright/test";
import { OfflineManager, type StoredMessage } from "../src/offline/offlineManager";

function installBrowserMocks(online = true): void {
  const listeners = new Map<string, Set<(event: Event) => void>>();
  const storage = new Map<string, string>();

  const localStorageMock = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => {
      storage.set(key, value);
    },
    removeItem: (key: string) => {
      storage.delete(key);
    },
  };

  const windowMock = {
    addEventListener: (type: string, callback: (event: Event) => void) => {
      if (!listeners.has(type)) {
        listeners.set(type, new Set());
      }
      listeners.get(type)?.add(callback);
    },
    removeEventListener: (type: string, callback: (event: Event) => void) => {
      listeners.get(type)?.delete(callback);
    },
    dispatchEvent: (event: Event) => {
      listeners.get(event.type)?.forEach((callback) => callback(event));
      return true;
    },
  };

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    writable: true,
    value: windowMock,
  });

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    writable: true,
    value: {
      onLine: online,
    },
  });

  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    writable: true,
    value: localStorageMock,
  });

  Object.defineProperty(globalThis, "CustomEvent", {
    configurable: true,
    writable: true,
    value: class MockCustomEvent {
      public type: string;
      public detail?: unknown;

      constructor(type: string, init?: { detail?: unknown }) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
  });
}

function userMessage(id: string, synced = false): StoredMessage {
  return {
    id,
    role: "user",
    content: `message-${id}`,
    timestamp: Date.now(),
    synced,
  };
}

test.describe("OfflineManager replay hardening", () => {
  test("deduplicates queued messages by id", () => {
    installBrowserMocks(false);
    const manager = new OfflineManager("session-1");

    manager.saveMessage(userMessage("m1", false));
    manager.saveMessage(userMessage("m1", false));

    expect(manager.getPendingSyncCount()).toBe(1);
  });

  test("replays queue once and marks messages synced", async () => {
    installBrowserMocks(true);
    const manager = new OfflineManager("session-2");

    manager.saveMessage(userMessage("m2", false));
    manager.saveMessage(userMessage("m3", false));

    const replayed: string[] = [];
    const result = await manager.replayQueue(async (message) => {
      replayed.push(message.id);
    });

    expect(result.replayed).toBe(2);
    expect(result.failed).toBe(0);
    expect(replayed).toEqual(["m2", "m3"]);
    expect(manager.getPendingSyncCount()).toBe(0);
    expect(manager.getSyncState()).toBe("synced");
  });

  test("keeps failed replay messages pending", async () => {
    installBrowserMocks(true);
    const manager = new OfflineManager("session-3");

    manager.saveMessage(userMessage("m4", false));

    const result = await manager.replayQueue(async () => {
      throw new Error("network down");
    });

    expect(result.replayed).toBe(0);
    expect(result.failed).toBe(1);
    expect(manager.getPendingSyncCount()).toBe(1);
    expect(manager.getSyncState()).toBe("retrying");
  });
});
