/**
 * AXE Event Telemetry Hook
 *
 * Captures and uploads user interactions for analytics and training.
 *
 * **Features:**
 * - Privacy-aware (respects anonymization settings)
 * - Batch uploads every 30 seconds
 * - Local queueing with retry
 * - DSGVO-compliant
 *
 * **Usage:**
 * ```typescript
 * const { trackEvent, stats } = useEventTelemetry({
 *   sessionId: 'session-abc123',
 *   appId: 'widget-test',
 *   anonymizationLevel: 'pseudonymized'
 * });
 *
 * trackEvent('axe_message', {
 *   message: 'Hello AXE',
 *   role: 'user'
 * });
 * ```
 */
import { useEffect, useRef, useCallback, useState } from 'react';

export type AxeEventType =
  | 'axe_message'
  | 'axe_feedback'
  | 'axe_click'
  | 'axe_context_snapshot'
  | 'axe_error'
  | 'axe_file_open'
  | 'axe_file_save'
  | 'axe_diff_applied'
  | 'axe_diff_rejected'
  | 'axe_session_start'
  | 'axe_session_end';

export type AnonymizationLevel = 'none' | 'pseudonymized' | 'strict';

interface AxeEventCreate {
  event_type: AxeEventType;
  session_id: string;
  app_id: string;
  user_id?: string;
  anonymization_level: AnonymizationLevel;
  event_data: Record<string, any>;
  client_timestamp: string;
  is_training_data: boolean;
  client_version?: string;
  client_platform?: string;
}

interface UseEventTelemetryOptions {
  backendUrl: string;
  sessionId: string;
  appId: string;
  userId?: string;
  anonymizationLevel?: AnonymizationLevel;
  telemetryEnabled?: boolean;
  trainingOptIn?: boolean;
  uploadInterval?: number; // milliseconds (default 30000)
  maxBatchSize?: number; // max events per batch (default 100)
}

interface TelemetryStats {
  queuedEvents: number;
  uploadedEvents: number;
  failedUploads: number;
  lastUploadTime: Date | null;
}

export function useEventTelemetry({
  backendUrl,
  sessionId,
  appId,
  userId,
  anonymizationLevel = 'pseudonymized',
  telemetryEnabled = true,
  trainingOptIn = false,
  uploadInterval = 30000,
  maxBatchSize = 100,
}: UseEventTelemetryOptions) {
  const eventQueue = useRef<AxeEventCreate[]>([]);
  const uploadTimer = useRef<NodeJS.Timeout | null>(null);
  const isUploading = useRef(false);

  const [stats, setStats] = useState<TelemetryStats>({
    queuedEvents: 0,
    uploadedEvents: 0,
    failedUploads: 0,
    lastUploadTime: null,
  });

  /**
   * Track a new event (adds to queue).
   */
  const trackEvent = useCallback(
    (eventType: AxeEventType, eventData: Record<string, any>) => {
      if (!telemetryEnabled) {
        return;
      }

      const event: AxeEventCreate = {
        event_type: eventType,
        session_id: sessionId,
        app_id: appId,
        user_id: userId,
        anonymization_level: anonymizationLevel,
        event_data: eventData,
        client_timestamp: new Date().toISOString(),
        is_training_data: trainingOptIn,
        client_version: '1.0.0', // TODO: Get from package.json
        client_platform: typeof window !== 'undefined' ? window.navigator.userAgent : 'unknown',
      };

      eventQueue.current.push(event);

      setStats((prev) => ({
        ...prev,
        queuedEvents: eventQueue.current.length,
      }));

      // If queue exceeds batch size, upload immediately
      if (eventQueue.current.length >= maxBatchSize) {
        uploadEvents();
      }
    },
    [
      telemetryEnabled,
      sessionId,
      appId,
      userId,
      anonymizationLevel,
      trainingOptIn,
      maxBatchSize,
    ]
  );

  /**
   * Upload queued events to backend.
   */
  const uploadEvents = useCallback(async () => {
    if (isUploading.current || eventQueue.current.length === 0) {
      return;
    }

    isUploading.current = true;

    // Take events from queue (up to batch size)
    const eventsToUpload = eventQueue.current.splice(0, maxBatchSize);

    try {
      const response = await fetch(`${backendUrl}/api/axe/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          events: eventsToUpload,
        }),
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      // Success
      setStats((prev) => ({
        ...prev,
        queuedEvents: eventQueue.current.length,
        uploadedEvents: prev.uploadedEvents + eventsToUpload.length,
        lastUploadTime: new Date(),
      }));

      console.log(`[Telemetry] Uploaded ${eventsToUpload.length} events`);
    } catch (error) {
      console.error('[Telemetry] Upload failed:', error);

      // Re-queue failed events (at the front)
      eventQueue.current.unshift(...eventsToUpload);

      setStats((prev) => ({
        ...prev,
        failedUploads: prev.failedUploads + 1,
        queuedEvents: eventQueue.current.length,
      }));
    } finally {
      isUploading.current = false;
    }
  }, [backendUrl, maxBatchSize]);

  /**
   * Track session start (auto-called on mount).
   */
  const trackSessionStart = useCallback(() => {
    trackEvent('axe_session_start', {
      timestamp: Date.now(),
      user_agent: typeof window !== 'undefined' ? window.navigator.userAgent : 'unknown',
    });
  }, [trackEvent]);

  /**
   * Track session end (auto-called on unmount).
   */
  const trackSessionEnd = useCallback(() => {
    trackEvent('axe_session_end', {
      timestamp: Date.now(),
      duration_ms: Date.now(), // TODO: Track actual session duration
    });
  }, [trackEvent]);

  /**
   * Helper: Track message event.
   */
  const trackMessage = useCallback(
    (role: 'user' | 'assistant', message: string, metadata?: Record<string, any>) => {
      trackEvent('axe_message', {
        role,
        message,
        ...metadata,
      });
    },
    [trackEvent]
  );

  /**
   * Helper: Track click event.
   */
  const trackClick = useCallback(
    (element: string, metadata?: Record<string, any>) => {
      trackEvent('axe_click', {
        element,
        ...metadata,
      });
    },
    [trackEvent]
  );

  /**
   * Helper: Track diff action.
   */
  const trackDiffAction = useCallback(
    (action: 'applied' | 'rejected', diffId: string, metadata?: Record<string, any>) => {
      trackEvent(
        action === 'applied' ? 'axe_diff_applied' : 'axe_diff_rejected',
        {
          diff_id: diffId,
          ...metadata,
        }
      );
    },
    [trackEvent]
  );

  /**
   * Helper: Track error.
   */
  const trackError = useCallback(
    (error: Error | string, metadata?: Record<string, any>) => {
      trackEvent('axe_error', {
        error: error instanceof Error ? error.message : error,
        stack: error instanceof Error ? error.stack : undefined,
        ...metadata,
      });
    },
    [trackEvent]
  );

  /**
   * Flush all queued events immediately.
   */
  const flushEvents = useCallback(async () => {
    await uploadEvents();
  }, [uploadEvents]);

  // Auto-upload every uploadInterval
  useEffect(() => {
    if (!telemetryEnabled) {
      return;
    }

    uploadTimer.current = setInterval(() => {
      uploadEvents();
    }, uploadInterval);

    return () => {
      if (uploadTimer.current) {
        clearInterval(uploadTimer.current);
      }
    };
  }, [telemetryEnabled, uploadInterval, uploadEvents]);

  // Track session start on mount
  useEffect(() => {
    if (telemetryEnabled) {
      trackSessionStart();
    }
  }, [telemetryEnabled, trackSessionStart]);

  // Track session end and flush on unmount
  useEffect(() => {
    return () => {
      if (telemetryEnabled) {
        trackSessionEnd();
        // Flush remaining events
        flushEvents();
      }
    };
  }, [telemetryEnabled, trackSessionEnd, flushEvents]);

  return {
    trackEvent,
    trackMessage,
    trackClick,
    trackDiffAction,
    trackError,
    flushEvents,
    stats,
  };
}
