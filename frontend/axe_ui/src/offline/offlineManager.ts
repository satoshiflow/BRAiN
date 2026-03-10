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

const STORAGE_PREFIX = "axe_offline_";
const MESSAGE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

/**
 * Offline storage and sync manager
 */
export class OfflineManager {
  private sessionId: string;
  private isOnline = typeof navigator !== "undefined" ? navigator.onLine : true;
  private syncQueue: StoredMessage[] = [];

  constructor(sessionId: string) {
    this.sessionId = sessionId;

    // Monitor online/offline status
    if (typeof window !== "undefined") {
      window.addEventListener("online", () => this.handleOnline());
      window.addEventListener("offline", () => this.handleOffline());
    }
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
      session.messages.push(message);
      session.lastModifiedAt = Date.now();

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
      window.removeEventListener("online", () => this.handleOnline());
      window.removeEventListener("offline", () => this.handleOffline());
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
