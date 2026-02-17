import { useState, useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface MissionEvent {
  type: 'mission_update' | 'mission_created' | 'mission_completed';
  mission_id: string;
  status?: string;
  timestamp: string;
}

export function useMissionWebSocket(enabled: boolean = true) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  const connect = useCallback(() => {
    if (!enabled) return;

    const baseUrl = process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://localhost:8000';
    const wsUrl = baseUrl.replace(/^http/, 'ws') + '/api/v1/system/ws';

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data: MissionEvent = JSON.parse(event.data);

        // Invalidate mission queries to refetch
        if (data.type.includes('mission')) {
          queryClient.invalidateQueries({ queryKey: ['missions'] });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (event) => {
      setError(event);
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Auto-reconnect after 3 seconds
      setTimeout(() => connect(), 3000);
    };

    wsRef.current = ws;
  }, [enabled, queryClient]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected, error };
}
