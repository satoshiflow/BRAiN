import { useEffect, useRef, useState, useCallback } from "react";
import { getApiBase } from "@/lib/config";

export interface AXERunEvent {
  event_type: string;
  run_id: string;
  sequence: number;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface UseAXERunStreamOptions {
  runId: string | null;
  token: string;
  onStateChange?: (state: string) => void;
  onTokenDelta?: (delta: string, finishReason?: string) => void;
  onComplete?: (output: Record<string, unknown>) => void;
  onError?: (error: string) => void;
}

export function useAXERunStream({
  runId,
  token,
  onStateChange,
  onTokenDelta,
  onComplete,
  onError,
}: UseAXERunStreamOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    if (!runId || !token) {
      return;
    }

    disconnect();
    setError(null);

    const apiBase = getApiBase();
    const eventSource = new EventSource(`${apiBase}/api/axe/runs/${runId}/events`, {
      withCredentials: true,
    });

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
    };

    eventSource.onerror = () => {
      setConnected(false);
      setError("SSE connection failed");
      eventSource.close();
    };

    eventSource.addEventListener("axe.run.state_changed", (event) => {
      try {
        const data = JSON.parse(event.data);
        onStateChange?.(data.data.current_state);
      } catch {
        // Ignore parse errors
      }
    });

    eventSource.addEventListener("axe.token.stream", (event) => {
      try {
        const data = JSON.parse(event.data);
        onTokenDelta?.(data.data.delta, undefined);
      } catch {
        // Ignore parse errors
      }
    });

    eventSource.addEventListener("axe.token.complete", (event) => {
      try {
        const data = JSON.parse(event.data);
        onTokenDelta?.(data.data.delta, data.data.finish_reason);
      } catch {
        // Ignore parse errors
      }
    });

    eventSource.addEventListener("axe.run.succeeded", (event) => {
      try {
        const data = JSON.parse(event.data);
        onComplete?.(data.data);
      } catch {
        // Ignore parse errors
      }
    });

    eventSource.addEventListener("axe.run.failed", (event) => {
      try {
        const data = JSON.parse(event.data);
        onError?.(data.data.message);
      } catch {
        // Ignore parse errors
      }
    });

    eventSource.addEventListener("axe.error", (event) => {
      try {
        const data = JSON.parse(event.data);
        onError?.(data.data.message);
      } catch {
        // Ignore parse errors
      }
    });

    eventSourceRef.current = eventSource;

    return () => {
      disconnect();
    };
  }, [runId, token, onStateChange, onTokenDelta, onComplete, onError, disconnect]);

  return { connected, error, disconnect };
}
