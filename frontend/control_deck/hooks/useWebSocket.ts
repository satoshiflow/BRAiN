/**
 * WebSocket Hooks - Real-time data streaming for dashboards
 */

import { useEffect, useRef, useState, useCallback } from "react";

// ========== Types ==========

export type WebSocketMessage =
  | HealthMetricMessage
  | AnomalyDetectedMessage
  | SimulatorStatusMessage
  | TaskAllocatedMessage
  | FormationUpdatedMessage
  | PongMessage
  | EchoMessage;

export interface HealthMetricMessage {
  type: "health_metric";
  component_id: string;
  health_score: number;
  timestamp: number;
}

export interface AnomalyDetectedMessage {
  type: "anomaly_detected";
  anomaly_type: string;
  severity: string;
  component_id: string;
  timestamp: number;
}

export interface SimulatorStatusMessage {
  type: "simulator_status";
  status: "running" | "stopped";
  robot_count: number;
  timestamp: number;
}

export interface TaskAllocatedMessage {
  type: "task_allocated";
  task_id: string;
  robot_ids: string[];
  timestamp: number;
}

export interface FormationUpdatedMessage {
  type: "formation_updated";
  formation_id: string;
  formation_type: string;
  timestamp: number;
}

export interface PongMessage {
  type: "pong";
  timestamp: number;
}

export interface EchoMessage {
  type: "echo";
  data: string;
}

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

export interface WebSocketHookResult {
  status: WebSocketStatus;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: string) => void;
  disconnect: () => void;
  reconnect: () => void;
}

// ========== Configuration ==========

const WS_BASE_URL =
  typeof window !== "undefined"
    ? `ws://${window.location.hostname}:8000/api/ws`
    : "ws://localhost:8000/api/ws";

const RECONNECT_INTERVAL = 3000; // 3 seconds
const PING_INTERVAL = 30000; // 30 seconds

// ========== Base WebSocket Hook ==========

export function useWebSocket(channel: string): WebSocketHookResult {
  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnect = useRef(true);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = `${WS_BASE_URL}/${channel}`;
    console.log(`[WebSocket] Connecting to ${wsUrl}...`);

    try {
      setStatus("connecting");
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`[WebSocket] Connected to ${channel}`);
        setStatus("connected");

        // Start ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error(`[WebSocket] Error on ${channel}:`, error);
        setStatus("error");
      };

      ws.onclose = () => {
        console.log(`[WebSocket] Disconnected from ${channel}`);
        setStatus("disconnected");

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt reconnect if allowed
        if (shouldReconnect.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`[WebSocket] Reconnecting to ${channel}...`);
            connect();
          }, RECONNECT_INTERVAL);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error(`[WebSocket] Connection failed:`, error);
      setStatus("error");
    }
  }, [channel]);

  const disconnect = useCallback(() => {
    shouldReconnect.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus("disconnected");
  }, []);

  const reconnect = useCallback(() => {
    shouldReconnect.current = true;
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn("[WebSocket] Cannot send message: not connected");
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      shouldReconnect.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect,
  };
}

// ========== Channel-Specific Hooks ==========

export function useMaintenanceWebSocket() {
  return useWebSocket("maintenance");
}

export function useSimulatorWebSocket() {
  return useWebSocket("simulator");
}

export function useCollaborationWebSocket() {
  return useWebSocket("collaboration");
}

export function useNavigationWebSocket() {
  return useWebSocket("navigation");
}

// ========== Message Filter Hook ==========

export function useWebSocketMessages<T extends WebSocketMessage>(
  channel: string,
  messageType: T["type"]
): T[] {
  const { lastMessage } = useWebSocket(channel);
  const [messages, setMessages] = useState<T[]>([]);

  useEffect(() => {
    if (lastMessage && lastMessage.type === messageType) {
      setMessages((prev) => [...prev, lastMessage as T]);
    }
  }, [lastMessage, messageType]);

  return messages;
}
