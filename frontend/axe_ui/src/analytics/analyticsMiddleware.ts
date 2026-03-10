/**
 * Analytics Middleware for AXE Widget
 * 
 * Tracks widget events and sends to webhook or analytics endpoint.
 * Supports batching, retries, and offline queue.
 */

export interface AnalyticsEvent {
  eventName: string;
  appId: string;
  sessionId: string;
  timestamp: string;
  data?: Record<string, unknown>;
  metadata?: {
    userAgent?: string;
    origin?: string;
    language?: string;
    timezone?: string;
  };
}

export interface AnalyticsConfig {
  webhookUrl?: string;
  batchSize?: number;
  batchInterval?: number;
  maxQueueSize?: number;
  retryAttempts?: number;
  retryDelay?: number;
  debug?: boolean;
}

export class AnalyticsMiddleware {
  private config: Required<AnalyticsConfig>;
  private eventQueue: AnalyticsEvent[] = [];
  private batchTimer: NodeJS.Timeout | null = null;
  private sending = false;

  constructor(config: AnalyticsConfig = {}) {
    this.config = {
      webhookUrl: config.webhookUrl || "",
      batchSize: config.batchSize || 10,
      batchInterval: config.batchInterval || 5000, // 5 seconds
      maxQueueSize: config.maxQueueSize || 1000,
      retryAttempts: config.retryAttempts || 3,
      retryDelay: config.retryDelay || 1000,
      debug: config.debug || false,
    };

    if (this.config.debug) {
      console.log("[Analytics] Middleware initialized", this.config);
    }
  }

  /**
   * Track an event
   */
  track(event: AnalyticsEvent): void {
    if (!this.config.webhookUrl) {
      if (this.config.debug) {
        console.log("[Analytics] No webhook configured, logging event locally:", event);
      }
      return;
    }

    // Check queue size
    if (this.eventQueue.length >= this.config.maxQueueSize) {
      console.warn("[Analytics] Event queue full, dropping oldest event");
      this.eventQueue.shift();
    }

    // Add metadata if missing
    if (!event.metadata) {
      event.metadata = this.getMetadata();
    }

    this.eventQueue.push(event);

    if (this.config.debug) {
      console.log("[Analytics] Event queued", { event, queueSize: this.eventQueue.length });
    }

    // Flush if batch size reached
    if (this.eventQueue.length >= this.config.batchSize) {
      this.flush();
    } else {
      // Schedule flush
      this.scheduleFlush();
    }
  }

  /**
   * Manually flush pending events
   */
  async flush(): Promise<boolean> {
    if (this.eventQueue.length === 0) {
      return true;
    }

    if (this.sending) {
      if (this.config.debug) {
        console.log("[Analytics] Already sending, skipping flush");
      }
      return false;
    }

    this.sending = true;

    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }

    const batch = this.eventQueue.splice(0, this.config.batchSize);

    try {
      await this.sendBatch(batch);
      this.sending = false;
      return true;
    } catch {
      // Put events back if send failed
      this.eventQueue.unshift(...batch);
      this.sending = false;
      return false;
    }
  }

  /**
   * Send a batch of events to webhook
   */
  private   async sendBatch(events: AnalyticsEvent[], attempt = 1): Promise<void> {
    if (!this.config.webhookUrl) return;

    try {
      const response = await fetch(this.config.webhookUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          events,
          batchSize: events.length,
          sentAt: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (this.config.debug) {
        console.log("[Analytics] Batch sent successfully", { batchSize: events.length });
      }
    } catch (err) {
      if (attempt < this.config.retryAttempts) {
        if (this.config.debug) {
          console.log(`[Analytics] Retry attempt ${attempt}/${this.config.retryAttempts}`);
        }

        // Exponential backoff
        const delay = this.config.retryDelay * Math.pow(2, attempt - 1);
        await new Promise((resolve) => setTimeout(resolve, delay));

        return this.sendBatch(events, attempt + 1);
      }

      console.error("[Analytics] Failed to send batch after retries:", err);
      throw err;
    }
  }

  /**
   * Schedule a flush after the batch interval
   */
  private scheduleFlush(): void {
    if (this.batchTimer) return;

    this.batchTimer = setTimeout(() => {
      this.batchTimer = null;
      if (this.eventQueue.length > 0) {
        this.flush();
      }
    }, this.config.batchInterval);
  }

  /**
   * Get browser/environment metadata
   */
  private getMetadata(): AnalyticsEvent["metadata"] {
    try {
      return {
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
        origin: typeof window !== "undefined" ? window.location.origin : undefined,
        language: typeof navigator !== "undefined" ? navigator.language : undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      };
    } catch {
      return {};
    }
  }

  /**
   * Get current queue size
   */
  getQueueSize(): number {
    return this.eventQueue.length;
  }

  /**
   * Clear the event queue
   */
  clear(): void {
    this.eventQueue = [];
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }
  }

  /**
   * Destroy the middleware
   */
  async destroy(): Promise<void> {
    // Final flush
    if (this.eventQueue.length > 0) {
      try {
        await this.flush();
      } catch (error) {
        console.warn("[Analytics] Final flush failed:", error);
      }
    }

    this.clear();
  }
}

// Singleton instance
let analyticsInstance: AnalyticsMiddleware | null = null;

/**
 * Initialize global analytics
 */
export function initializeAnalytics(config: AnalyticsConfig): AnalyticsMiddleware {
  if (analyticsInstance) {
    console.warn("[Analytics] Already initialized, returning existing instance");
    return analyticsInstance;
  }

  analyticsInstance = new AnalyticsMiddleware(config);
  return analyticsInstance;
}

/**
 * Get global analytics instance
 */
export function getAnalytics(): AnalyticsMiddleware | null {
  return analyticsInstance;
}
