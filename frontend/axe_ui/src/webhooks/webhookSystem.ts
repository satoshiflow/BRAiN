/**
 * Webhook System for AXE Widget
 * 
 * Sends events to external sites with retry logic, backoff, and queue persistence.
 */

import {
  buildSignatureInput,
  createHmacSha256Signature,
  isTimestampInReplayWindow,
} from "@/src/webhooks/security";

export type WebhookEventType =
  | "widget.opened"
  | "widget.closed"
  | "widget.ready"
  | "message.sent"
  | "message.received"
  | "error.occurred"
  | "plugin.registered"
  | "plugin.unregistered";

export interface WebhookPayload {
  eventType: WebhookEventType;
  appId: string;
  sessionId: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface WebhookConfig {
  url: string;
  secret?: string; // For HMAC signature verification
  replayWindowMs?: number;
  timeout?: number;
  maxRetries?: number;
  backoffMultiplier?: number;
  debug?: boolean;
}

export interface WebhookRequest {
  id: string;
  payload: WebhookPayload;
  timestamp: string;
  attempt: number;
  nextRetryAt?: number;
}

/**
 * Webhook system for sending events to external endpoints
 */
export class WebhookSystem {
  private config: Required<WebhookConfig>;
  private queue: Map<string, WebhookRequest> = new Map();
  private seenRequestIds: Map<string, number> = new Map();
  private processing = false;
  private processInterval: NodeJS.Timeout | null = null;

  constructor(config: WebhookConfig) {
    this.config = {
      url: config.url,
      secret: config.secret || "",
      replayWindowMs: config.replayWindowMs || 5 * 60 * 1000,
      timeout: config.timeout || 10000,
      maxRetries: config.maxRetries || 3,
      backoffMultiplier: config.backoffMultiplier || 2,
      debug: config.debug || false,
    };

    // Start processing queue periodically
    this.startProcessor();
  }

  /**
   * Send a webhook event
   */
  async send(payload: WebhookPayload): Promise<boolean> {
    try {
      const request: WebhookRequest = {
        id: `webhook_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
        payload,
        timestamp: new Date().toISOString(),
        attempt: 0,
      };

      this.log("info", `Event queued: ${payload.eventType}`, { requestId: request.id });

      this.queue.set(request.id, request);
      return true;
    } catch (error) {
      this.log("error", "Failed to queue webhook", error);
      return false;
    }
  }

  /**
   * Process pending webhooks
   */
  private async processQueue(): Promise<void> {
    if (this.processing || this.queue.size === 0) {
      return;
    }

    this.processing = true;

    try {
      const requests = Array.from(this.queue.values());

      for (const request of requests) {
        if (!this.shouldProcessRequest(request)) {
          this.queue.delete(request.id);
          continue;
        }

        // Check if should retry
        if (request.nextRetryAt && request.nextRetryAt > Date.now()) {
          continue;
        }

        if (request.attempt >= this.config.maxRetries) {
          this.log("warn", "Webhook max retries exceeded, dropping", {
            requestId: request.id,
            eventType: request.payload.eventType,
          });
          this.queue.delete(request.id);
          continue;
        }

        try {
          await this.sendRequest(request);
          this.seenRequestIds.set(request.id, Date.now());
          this.queue.delete(request.id);
          this.log("info", "Webhook sent successfully", {
            requestId: request.id,
            eventType: request.payload.eventType,
          });
        } catch (error) {
          request.attempt++;
          const delay = this.getBackoffDelay(request.attempt);
          request.nextRetryAt = Date.now() + delay;

          this.log("warn", `Webhook send failed, retrying in ${delay}ms`, {
            requestId: request.id,
            attempt: request.attempt,
            error,
          });
        }
      }
    } finally {
      this.processing = false;
    }
  }

  /**
   * Send a single webhook request
   */
  private async sendRequest(request: WebhookRequest): Promise<void> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const payloadJson = JSON.stringify(request.payload);
      const signature = this.config.secret
        ? await createHmacSha256Signature(
            this.config.secret,
            buildSignatureInput(request.timestamp, request.id, payloadJson)
          )
        : "";

      const response = await fetch(this.config.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-AXE-Signature": signature ? `v1=${signature}` : "",
          "X-AXE-Request-Id": request.id,
          "X-AXE-Timestamp": request.timestamp,
          "X-AXE-Retry-Attempt": String(request.attempt),
        },
        body: payloadJson,
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } finally {
      clearTimeout(timeout);
    }
  }

  private shouldProcessRequest(request: WebhookRequest): boolean {
    this.pruneReplayCache();

    if (!isTimestampInReplayWindow(request.timestamp, this.config.replayWindowMs)) {
      this.log("warn", "Dropping webhook outside replay window", {
        requestId: request.id,
        timestamp: request.timestamp,
      });
      return false;
    }

    if (this.seenRequestIds.has(request.id)) {
      this.log("warn", "Dropping replayed webhook request id", {
        requestId: request.id,
      });
      return false;
    }

    return true;
  }

  private pruneReplayCache(): void {
    const cutoff = Date.now() - this.config.replayWindowMs;
    for (const [requestId, seenAt] of this.seenRequestIds.entries()) {
      if (seenAt < cutoff) {
        this.seenRequestIds.delete(requestId);
      }
    }
  }

  /**
   * Calculate exponential backoff delay
   */
  private getBackoffDelay(attempt: number): number {
    const baseDelay = 1000; // 1 second
    return baseDelay * Math.pow(this.config.backoffMultiplier, attempt - 1);
  }

  /**
   * Start processing queue
   */
  private startProcessor(): void {
    this.processInterval = setInterval(() => {
      this.processQueue();
    }, 5000); // Process every 5 seconds
  }

  /**
   * Get queue size
   */
  getQueueSize(): number {
    return this.queue.size;
  }

  /**
   * Get pending requests
   */
  getPendingRequests(): WebhookRequest[] {
    return Array.from(this.queue.values());
  }

  /**
   * Force process queue immediately
   */
  async flush(): Promise<void> {
    await this.processQueue();
  }

  /**
   * Clear queue
   */
  clear(): void {
    this.queue.clear();
    this.seenRequestIds.clear();
  }

  /**
   * Destroy webhook system
   */
  destroy(): void {
    if (this.processInterval) {
      clearInterval(this.processInterval);
    }
    this.queue.clear();
    this.seenRequestIds.clear();
  }

  /**
   * Debug logging
   */
  private log(level: string, message: string, data?: unknown): void {
    if (this.config.debug) {
      const prefix = `[Webhook:${level.toUpperCase()}]`;
      if (data) {
        console.log(prefix, message, data);
      } else {
        console.log(prefix, message);
      }
    }
  }
}

/**
 * Create webhook payload
 */
export function createWebhookPayload(
  eventType: WebhookEventType,
  appId: string,
  sessionId: string,
  data: Record<string, unknown> = {}
): WebhookPayload {
  return {
    eventType,
    appId,
    sessionId,
    timestamp: new Date().toISOString(),
    data,
  };
}
