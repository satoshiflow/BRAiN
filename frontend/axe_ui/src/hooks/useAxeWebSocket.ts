/**
 * useAxeWebSocket - WebSocket Hook for Real-Time AXE Communication
 *
 * Manages WebSocket connection to backend for:
 * - Real-time chat responses
 * - Code diff streaming
 * - File update notifications
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAxeStore } from '../store/axeStore';
import { useDiffStore } from '../store/diffStore';
import type { AxeMessage } from '../types';

interface WebSocketMessage {
  type: string;
  payload: any;
}

interface UseAxeWebSocketOptions {
  backendUrl: string;
  sessionId: string;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
}

export function useAxeWebSocket({
  backendUrl,
  sessionId,
  onConnected,
  onDisconnected,
  onError
}: UseAxeWebSocketOptions) {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const { addMessage } = useAxeStore();
  const { addDiff } = useDiffStore();

  // ============================================================================
  // Send Message Helper
  // ============================================================================

  const sendMessage = useCallback((type: string, payload: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type, payload }));
      return true;
    }
    return false;
  }, []);

  // ============================================================================
  // Send Chat Message
  // ============================================================================

  const sendChat = useCallback((message: string, metadata?: Record<string, any>) => {
    return sendMessage('chat', { message, metadata });
  }, [sendMessage]);

  // ============================================================================
  // Send Diff Actions
  // ============================================================================

  const sendDiffApplied = useCallback((diffId: string) => {
    return sendMessage('diff_applied', { diff_id: diffId });
  }, [sendMessage]);

  const sendDiffRejected = useCallback((diffId: string) => {
    return sendMessage('diff_rejected', { diff_id: diffId });
  }, [sendMessage]);

  // ============================================================================
  // Send File Update
  // ============================================================================

  const sendFileUpdate = useCallback((fileId: string, content: string) => {
    return sendMessage('file_updated', { file_id: fileId, content });
  }, [sendMessage]);

  // ============================================================================
  // Connect/Disconnect
  // ============================================================================

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    const wsUrl = backendUrl.replace(/^http/, 'ws') + `/api/axe/ws/${sessionId}`;
    console.log('[AXE WebSocket] Connecting to:', wsUrl);

    try {
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log('[AXE WebSocket] Connected');
        setIsConnected(true);
        onConnected?.();

        // Send initial ping
        socket.send(JSON.stringify({
          type: 'ping',
          payload: { timestamp: Date.now() }
        }));
      };

      socket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[AXE WebSocket] Received:', message.type, message.payload);

          switch (message.type) {
            // Chat response from backend
            case 'chat_response': {
              const assistantMessage: AxeMessage = {
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: message.payload.message,
                timestamp: new Date().toISOString(),
                context: message.payload.metadata
              };
              addMessage(assistantMessage);
              break;
            }

            // Code diff for Apply/Reject
            case 'diff': {
              const diff = message.payload;
              addDiff(diff);
              break;
            }

            // File content update
            case 'file_update': {
              const { file_id, content } = message.payload;
              useAxeStore.getState().updateFile(file_id, content);
              break;
            }

            // Confirmations
            case 'diff_applied_confirmed':
            case 'diff_rejected_confirmed':
            case 'file_updated_confirmed':
              console.log('[AXE WebSocket] Confirmed:', message.type);
              break;

            // Pong (keep-alive response)
            case 'pong':
              console.log('[AXE WebSocket] Pong received');
              break;

            // Error
            case 'error':
              console.error('[AXE WebSocket] Error:', message.payload.message);
              onError?.(new Error(message.payload.message));
              break;

            default:
              console.warn('[AXE WebSocket] Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('[AXE WebSocket] Failed to parse message:', err);
        }
      };

      socket.onerror = (error) => {
        console.error('[AXE WebSocket] Error:', error);
        onError?.(new Error('WebSocket error'));
      };

      socket.onclose = () => {
        console.log('[AXE WebSocket] Disconnected');
        setIsConnected(false);
        onDisconnected?.();

        // Attempt reconnect after 3 seconds
        reconnectTimeout.current = setTimeout(() => {
          console.log('[AXE WebSocket] Attempting reconnect...');
          connect();
        }, 3000);
      };

      ws.current = socket;
    } catch (err) {
      console.error('[AXE WebSocket] Connection failed:', err);
      onError?.(err as Error);
    }
  }, [backendUrl, sessionId, onConnected, onDisconnected, onError, addMessage, addDiff]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    setIsConnected(false);
  }, []);

  // ============================================================================
  // Keep-Alive Ping (every 30 seconds)
  // ============================================================================

  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({
          type: 'ping',
          payload: { timestamp: Date.now() }
        }));
      }
    }, 30000); // 30 seconds

    return () => clearInterval(pingInterval);
  }, [isConnected]);

  // ============================================================================
  // Auto-connect on mount, cleanup on unmount
  // ============================================================================

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // ============================================================================
  // Return API
  // ============================================================================

  return {
    isConnected,
    connect,
    disconnect,
    sendChat,
    sendDiffApplied,
    sendDiffRejected,
    sendFileUpdate
  };
}
