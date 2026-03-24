/**
 * Offline Mode Manager for AXE Widget
 * 
 * Supports offline message caching, sync queue, and Service Worker integration.
 */

import type { AxeChatMessage } from "@/lib/contracts";

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  synced: boolean;
}

export interface OfflineSession {
  sessionId: string;
  messages: StoredMessage[];
  createdAt: number;
  lastModifiedAt: number;
}

export type SyncState = "offline" | "retrying" | "synced";

export interface ReplayResult {
  replayed: number;
  failed: number;
}

const STORAGE_PREFIX = "axe_offline_";
const MESSAGE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

/**
 * Offline storage and sync manager
 */
export class OfflineManager {
  private sessionId: string;
  private isOnline = typeof navigator !== "undefined" ? navigator.onLine : true;
  private syncQueue: StoredMessage[] = [];
  private replayInProgress = false;
  private onlineHandler = () => this.handleOnline();
  private offlineHandler = () => this.handleOffline();

  constructor(sessionId: string) {
    this.sessionId = sessionId;

    // Monitor online/offline status
    if (typeof window !== "undefined") {
      window.addEventListener("online", this.onlineHandler);
      window.addEventListener("offline", this.offlineHandler);
    }

    this.syncQueue = this.getUnsyncedMessages();
  }

  /**
   * Save a message to offline storage
   */
  saveMessage(message: StoredMessage): boolean {
    try {
      if (typeof localStorage === "undefined") {
        return false;
      }

      const session = this.getSession() || this.createSession();
      const existingIndex = session.messages.findIndex((stored) => stored.id === message.id);
      if (existingIndex >= 0) {
        session.messages[existingIndex] = message;
      } else {
        session.messages.push(message);
      }
      session.lastModifiedAt = Date.now();

      if (!message.synced) {
        this.enqueueForSync(message);
      }

      localStorage.setItem(this.getSessionKey(), JSON.stringify(session));
      return true;
    } catch (error) {
      console.warn("[OfflineManager] Failed to save message:", error);
      return false;
    }
  }

  /**
   * Get all messages for current session
   */
  getMessages(): AxeChatMessage[] {
    const session = this.getSession();
    if (!session) return [];

    return session.messages
      .filter((msg) => !msg.synced)
      .map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));
  }

  /**
   * Get unsynced messages
   */
  getUnsyncedMessages(): StoredMessage[] {
    const session = this.getSession();
    if (!session) return [];

    return session.messages.filter((msg) => !msg.synced);
  }

  /**
   * Mark message as synced
   */
  markAsSynced(messageId: string): boolean {
    try {
      const session = this.getSession();
      if (!session) return false;

      const message = session.messages.find((m) => m.id === messageId);
      if (!message) return false;

      message.synced = true;
      session.lastModifiedAt = Date.now();
      localStorage.setItem(this.getSessionKey(), JSON.stringify(session));
      this.syncQueue = this.syncQueue.filter((m) => m.id !== messageId);
      this.emitSyncState(this.isOnline ? "synced" : "offline");

      return true;
    } catch (error) {
      console.warn("[OfflineManager] Failed to mark message as synced:", error);
      return false;
    }
  }

  /**
   * Clear all unsynced messages
   */
  clearUnsyncedMessages(): void {
    try {
      const session = this.getSession();
      if (!session) return;

      session.messages = session.messages.filter((m) => m.synced);
      session.lastModifiedAt = Date.now();
      localStorage.setItem(this.getSessionKey(), JSON.stringify(session));
    } catch (error) {
      console.warn("[OfflineManager] Failed to clear unsynced messages:", error);
    }
  }

  /**
   * Get current session data
   */
  getSession(): OfflineSession | null {
    try {
      if (typeof localStorage === "undefined") {
        return null;
      }

      const data = localStorage.getItem(this.getSessionKey());
      if (!data) return null;

      return JSON.parse(data) as OfflineSession;
    } catch (error) {
      console.warn("[OfflineManager] Failed to get session:", error);
      return null;
    }
  }

  /**
   * Create a new offline session
   */
  private createSession(): OfflineSession {
    return {
      sessionId: this.sessionId,
      messages: [],
      createdAt: Date.now(),
      lastModifiedAt: Date.now(),
    };
  }

  /**
   * Check if online
   */
  isOnlineNow(): boolean {
    return this.isOnline;
  }

  /**
   * Handle coming online
   */
  private handleOnline(): void {
    this.isOnline = true;
    console.log("[OfflineManager] Online detected");
    this.emitSyncState("retrying");

    // Trigger sync event
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("axe-sync", { detail: { sessionId: this.sessionId } }));
    }
  }

  /**
   * Handle going offline
   */
  private handleOffline(): void {
    this.isOnline = false;
    console.log("[OfflineManager] Offline detected");
    this.emitSyncState("offline");

    // Trigger offline event
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("axe-offline", { detail: { sessionId: this.sessionId } }));
    }
  }

  /**
   * Clear expired sessions (> 7 days old)
   */
  static clearExpiredSessions(): void {
    try {
      if (typeof localStorage === "undefined") {
        return;
      }

      const now = Date.now();
      const keys = Object.keys(localStorage).filter((k) => k.startsWith(STORAGE_PREFIX));

      keys.forEach((key) => {
        const data = localStorage.getItem(key);
        if (!data) return;

        try {
          const session = JSON.parse(data) as OfflineSession;
          if (now - session.lastModifiedAt > MESSAGE_EXPIRY_MS) {
            localStorage.removeItem(key);
            console.log("[OfflineManager] Cleared expired session:", key);
          }
        } catch (error) {
          console.warn("[OfflineManager] Failed to parse session for cleanup:", error);
        }
      });
    } catch (error) {
      console.warn("[OfflineManager] Failed to clear expired sessions:", error);
    }
  }

  /**
   * Get storage key for session
   */
  private getSessionKey(): string {
    return `${STORAGE_PREFIX}${this.sessionId}`;
  }

  private enqueueForSync(message: StoredMessage): void {
    if (!this.syncQueue.some((queued) => queued.id === message.id)) {
      this.syncQueue.push(message);
    }
    this.emitSyncState(this.isOnline ? "retrying" : "offline");
  }

  private emitSyncState(state: SyncState): void {
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("axe-sync-state", {
          detail: {
            sessionId: this.sessionId,
            state,
            pending: this.syncQueue.length,
          },
        })
      );
    }
  }

  getSyncState(): SyncState {
    if (!this.isOnline) {
      return "offline";
    }
    if (this.replayInProgress || this.syncQueue.length > 0) {
      return "retrying";
    }
    return "synced";
  }

  getPendingSyncCount(): number {
    return this.syncQueue.length;
  }

  async replayQueue(
    replayHandler: (message: StoredMessage) => Promise<void>,
    options?: { perMessageTimeoutMs?: number }
  ): Promise<ReplayResult> {
    if (!this.isOnline || this.replayInProgress) {
      return { replayed: 0, failed: 0 };
    }

    this.replayInProgress = true;
    this.emitSyncState("retrying");

    const timeoutMs = options?.perMessageTimeoutMs ?? 10000;
    let replayed = 0;
    let failed = 0;

    try {
      const queueSnapshot = [...this.syncQueue];
      for (const message of queueSnapshot) {
        try {
          await Promise.race([
            replayHandler(message),
            new Promise<never>((_, reject) => {
              setTimeout(() => reject(new Error("Replay timeout")), timeoutMs);
            }),
          ]);
          this.markAsSynced(message.id);
          replayed += 1;
        } catch (error) {
          failed += 1;
          console.warn("[OfflineManager] Replay failed for message", message.id, error);
        }
      }
      return { replayed, failed };
    } finally {
      this.replayInProgress = false;
      this.emitSyncState(this.getSyncState());
    }
  }

  /**
   * Export session data
   */
  exportSession(): OfflineSession | null {
    return this.getSession();
  }

  /**
   * Import session data
   */
  importSession(session: OfflineSession): boolean {
    try {
      if (typeof localStorage === "undefined") {
        return false;
      }

      localStorage.setItem(this.getSessionKey(), JSON.stringify(session));
      return true;
    } catch (error) {
      console.warn("[OfflineManager] Failed to import session:", error);
      return false;
    }
  }

  /**
   * Destroy offline manager
   */
  destroy(): void {
    // Cleanup event listeners
    if (typeof window !== "undefined") {
      window.removeEventListener("online", this.onlineHandler);
      window.removeEventListener("offline", this.offlineHandler);
    }
  }
}

/**
 * Register Service Worker for offline support
 */
export async function registerOfflineSW(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) {
    console.warn("[OfflineManager] Service Worker not supported");
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
    });

    console.log("[OfflineManager] Service Worker registered");
    return registration;
  } catch (error) {
    console.warn("[OfflineManager] Service Worker registration failed:", error);
    return null;
  }
}

/**
 * Unregister Service Worker
 */
export async function unregisterOfflineSW(): Promise<void> {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      await registration.unregister();
    }
    console.log("[OfflineManager] Service Worker unregistered");
  } catch (error) {
    console.warn("[OfflineManager] Service Worker unregistration failed:", error);
  }
}
