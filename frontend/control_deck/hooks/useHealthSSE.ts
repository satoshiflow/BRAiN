import { useState, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface SSEEvent {
  channel: string;
  event_type: string;
  timestamp: number;
  data: any;
}

export function useHealthSSE(enabled: boolean = true) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;

    const baseUrl = process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://127.0.0.1:8000';
    const url = `${baseUrl}/api/system/stream`;

    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(url);

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data: SSEEvent = JSON.parse(event.data);

          if (data.event_type === 'health_update') {
            queryClient.invalidateQueries({ queryKey: ['health'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          }
          if (data.event_type === 'metrics_update') {
            queryClient.invalidateQueries({ queryKey: ['telemetry'] });
          }
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      eventSource.onerror = () => {
        // Silent fail - SSE ist optional
        setIsConnected(false);
        if (eventSource) {
          eventSource.close();
        }
      };

      eventSourceRef.current = eventSource;
    } catch (err) {
      // Silent fail - SSE ist optional
      setIsConnected(false);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [enabled, queryClient]);

  return { isConnected, error };
}
