/**
 * SSE Subscription Hook (Phase 3 Frontend)
 *
 * Custom React hook for Server-Sent Events subscription.
 * Provides real-time event streaming from NeuroRail backend.
 *
 * @example
 * ```tsx
 * const { events, isConnected, error } = useSSE({
 *   channels: ['audit', 'reflex'],
 *   eventTypes: ['execution_start', 'circuit_open'],
 *   onEvent: (event) => console.log(event),
 * });
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface SSEEventData {
  channel: string;
  event_type: string;
  timestamp: number;
  data: Record<string, any>;
}

export interface SSEOptions {
  /** Event channels to subscribe to (default: ['all']) */
  channels?: string[];
  /** Event types to filter */
  eventTypes?: string[];
  /** Entity IDs to filter (mission_id, job_id, etc.) */
  entityIds?: string[];
  /** Callback when event received */
  onEvent?: (event: SSEEventData) => void;
  /** Callback when connection established */
  onConnect?: () => void;
  /** Callback when connection closed */
  onDisconnect?: () => void;
  /** Callback on error */
  onError?: (error: Event) => void;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
}

export interface SSEHookReturn {
  /** All received events */
  events: SSEEventData[];
  /** Latest event */
  latestEvent: SSEEventData | null;
  /** Connection status */
  isConnected: boolean;
  /** Error if any */
  error: Event | null;
  /** Clear all events */
  clearEvents: () => void;
  /** Manually disconnect */
  disconnect: () => void;
  /** Manually reconnect */
  reconnect: () => void;
}

export function useSSE(options: SSEOptions = {}): SSEHookReturn {
  const {
    channels = ['all'],
    eventTypes,
    entityIds,
    onEvent,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectDelay = 3000,
  } = options;

  const [events, setEvents] = useState<SSEEventData[]>([]);
  const [latestEvent, setLatestEvent] = useState<SSEEventData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  // Build SSE URL with query params
  const buildSSEUrl = useCallback(() => {
    const baseUrl = process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://localhost:8000';
    const url = new URL('/api/neurorail/v1/stream/events', baseUrl);

    // Add channels
    channels.forEach(channel => url.searchParams.append('channels', channel));

    // Add event types
    if (eventTypes && eventTypes.length > 0) {
      eventTypes.forEach(type => url.searchParams.append('event_types', type));
    }

    // Add entity IDs
    if (entityIds && entityIds.length > 0) {
      entityIds.forEach(id => url.searchParams.append('entity_ids', id));
    }

    return url.toString();
  }, [channels, eventTypes, entityIds]);

  // Connect to SSE
  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = buildSSEUrl();
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      if (!mountedRef.current) return;
      setIsConnected(true);
      setError(null);
      onConnect?.();
    };

    eventSource.onerror = (event) => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      setError(event);
      onError?.(event);

      // Auto-reconnect
      if (autoReconnect && mountedRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current) {
            connect();
          }
        }, reconnectDelay);
      }
    };

    // Listen to all event types (SSE sends event type in "event:" field)
    // We'll add a generic message listener
    eventSource.onmessage = (event) => {
      if (!mountedRef.current) return;

      try {
        const eventData: SSEEventData = JSON.parse(event.data);

        setLatestEvent(eventData);
        setEvents((prev) => [...prev, eventData]);
        onEvent?.(eventData);
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSourceRef.current = eventSource;
  }, [buildSSEUrl, onConnect, onError, onEvent, autoReconnect, reconnectDelay]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
    onDisconnect?.();
  }, [onDisconnect]);

  // Reconnect
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(() => connect(), 100);
  }, [connect, disconnect]);

  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
    setLatestEvent(null);
  }, []);

  // Setup on mount
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    events,
    latestEvent,
    isConnected,
    error,
    clearEvents,
    disconnect,
    reconnect,
  };
}
