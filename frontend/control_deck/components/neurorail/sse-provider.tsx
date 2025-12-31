/**
 * SSE Provider Context (Phase 3 Frontend)
 *
 * Global SSE connection provider for ControlDeck.
 * Provides shared SSE connection to all child components.
 *
 * @example
 * ```tsx
 * <SSEProvider>
 *   <ControlDeckApp />
 * </SSEProvider>
 * ```
 */

"use client";

import React, { createContext, useContext, ReactNode } from 'react';
import { useSSE, SSEEventData, SSEHookReturn } from '@/hooks/use-sse';

interface SSEProviderProps {
  children: ReactNode;
  /** Initial channels to subscribe (default: ['all']) */
  channels?: string[];
}

const SSEContext = createContext<SSEHookReturn | null>(null);

export function SSEProvider({ children, channels = ['all'] }: SSEProviderProps) {
  const sseHook = useSSE({
    channels,
    autoReconnect: true,
    reconnectDelay: 3000,
    onConnect: () => console.log('[SSE] Connected'),
    onDisconnect: () => console.log('[SSE] Disconnected'),
    onError: (error) => console.error('[SSE] Error:', error),
  });

  return <SSEContext.Provider value={sseHook}>{children}</SSEContext.Provider>;
}

/**
 * Hook to access SSE context.
 * Must be used within SSEProvider.
 */
export function useSSEContext(): SSEHookReturn {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSEContext must be used within SSEProvider');
  }
  return context;
}

/**
 * Hook to filter SSE events by criteria.
 *
 * @example
 * ```tsx
 * const auditEvents = useFilteredSSE({
 *   channels: ['audit'],
 *   eventTypes: ['execution_start', 'execution_success'],
 * });
 * ```
 */
export function useFilteredSSE(filter: {
  channels?: string[];
  eventTypes?: string[];
  entityIds?: string[];
}): SSEEventData[] {
  const { events } = useSSEContext();

  return events.filter((event) => {
    // Filter by channel
    if (filter.channels && filter.channels.length > 0) {
      if (!filter.channels.includes(event.channel) && !filter.channels.includes('all')) {
        return false;
      }
    }

    // Filter by event type
    if (filter.eventTypes && filter.eventTypes.length > 0) {
      if (!filter.eventTypes.includes(event.event_type)) {
        return false;
      }
    }

    // Filter by entity IDs
    if (filter.entityIds && filter.entityIds.length > 0) {
      const eventEntityIds = [
        event.data.mission_id,
        event.data.plan_id,
        event.data.job_id,
        event.data.attempt_id,
      ].filter(Boolean);

      if (!eventEntityIds.some(id => filter.entityIds!.includes(id))) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Hook to get latest event matching criteria.
 */
export function useLatestSSEEvent(filter: {
  channels?: string[];
  eventTypes?: string[];
}): SSEEventData | null {
  const { latestEvent } = useSSEContext();

  if (!latestEvent) return null;

  // Check if latest event matches filter
  if (filter.channels && filter.channels.length > 0) {
    if (!filter.channels.includes(latestEvent.channel) && !filter.channels.includes('all')) {
      return null;
    }
  }

  if (filter.eventTypes && filter.eventTypes.length > 0) {
    if (!filter.eventTypes.includes(latestEvent.event_type)) {
      return null;
    }
  }

  return latestEvent;
}
