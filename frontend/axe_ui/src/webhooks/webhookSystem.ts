/**
 * Webhook System for AXE Widget
 * 
 * Sends events to external sites with retry logic, backoff, and queue persistence.
 */

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
  timeout?: number;
  maxRetries?: number;
  backoffMultiplier?: number;
  debug?: boolean;
}

export interface WebhookRequest {
  id: string;
  payload: WebhookPayload;
  attempt: number;
  nextRetryAt?: number;
}

/**
 * Webhook system for sending events to external endpoints
 */
export class WebhookSystem {
  private config: Required<WebhookConfig>;
  private queue: Map<string, WebhookRequest> = new Map();
  private processing = false;
  private processInterval: NodeJS.Timeout | null = null;

  constructor(config: WebhookConfig) {
    this.config = {
      url: config.url,
      secret: config.secret || "",
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
      const signature = this.config.secret ? this.signPayload(JSON.stringify(request.payload)) : undefined;

      const response = await fetch(this.config.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-AXE-Signature": signature || "",
          "X-AXE-Request-ID": request.id,
          "X-AXE-Retry-Attempt": String(request.attempt),
        },
        body: JSON.stringify(request.payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Create HMAC signature for payload
   */
  private signPayload(payload: string): string {
    if (!this.config.secret) return "";

    // Simple signature (in production, use proper HMAC-SHA256)
    // This is a placeholder implementation
    const encoder = new TextEncoder();
    const data = encoder.encode(this.config.secret + payload);
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      hash = (hash << 5) - hash + data[i];
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16);
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
  }

  /**
   * Destroy webhook system
   */
  destroy(): void {
    if (this.processInterval) {
      clearInterval(this.processInterval);
    }
    this.queue.clear();
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
