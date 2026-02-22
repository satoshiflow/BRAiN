// API Client für BRAiN Backend
// Axios-basiert mit Interceptors für Error Handling

import { QueryClient } from '@tanstack/react-query';

// API Base URL - muss HTTPS sein für Production
// Im Browser: relative URL (gleicher Origin) oder explizite HTTPS-URL
const API_BASE = typeof window !== 'undefined' 
  ? (process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'https://api.brain.falklabs.de')
  : 'http://backend:8000'; // Server-side rendering (Docker intern)

// Types
export interface Mission {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: number;
  score: number;
  created_at: string;
  progress?: number;
  agent?: string;
}

export interface MissionQueueResponse {
  items: Mission[];
  length: number;
}

export interface MissionHealth {
  status: 'ok' | 'degraded';
  details: {
    queue_healthy: boolean;
    queue_length: number;
    worker_running: boolean;
    worker_poll_interval?: number;
    redis_url?: string;
  };
}

export interface SystemEvent {
  id: string;
  event_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  details?: Record<string, unknown>;
  source: string;
  created_at: string;
}

export interface EventStats {
  total: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  recent_24h: number;
  last_event_at?: string;
}

export interface WorkerStatus {
  running: boolean;
  poll_interval?: number;
  redis_url?: string;
  last_check?: string;
}

// Error Handling
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Fetch Wrapper mit Error Handling
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || `HTTP ${response.status}`,
      response.status,
      errorData
    );
  }

  return response.json();
}

// API Functions
export const api = {
  // Missions
  missions: {
    getQueue: (limit = 20) => 
      fetchApi<MissionQueueResponse>(`/api/missions/queue?limit=${limit}`),
    
    getHealth: () => 
      fetchApi<MissionHealth>('/api/missions/health'),
    
    getWorkerStatus: () => 
      fetchApi<WorkerStatus>('/api/missions/worker/status'),
    
    enqueue: (payload: {
      type: string;
      payload: Record<string, unknown>;
      priority?: number;
      created_by?: string;
    }) => 
      fetchApi<{ mission_id: string; status: string }>('/api/missions/enqueue', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    
    getEvents: (limit = 100) => 
      fetchApi<{ events: SystemEvent[] }>(`/api/missions/events/history?limit=${limit}`),
  },

  // Events
  events: {
    getAll: (params?: { 
      limit?: number; 
      offset?: number; 
      event_type?: string; 
      severity?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set('limit', String(params.limit));
      if (params?.offset) searchParams.set('offset', String(params.offset));
      if (params?.event_type) searchParams.set('event_type', params.event_type);
      if (params?.severity) searchParams.set('severity', params.severity);
      
      return fetchApi<SystemEvent[]>(`/api/events?${searchParams.toString()}`);
    },
    
    getStats: () => 
      fetchApi<EventStats>('/api/events/stats'),
    
    create: (event: Omit<SystemEvent, 'id' | 'created_at'>) => 
      fetchApi<SystemEvent>('/api/events', {
        method: 'POST',
        body: JSON.stringify(event),
      }),
  },

  // Agents (Placeholder - erweitern wenn Backend verfügbar)
  agents: {
    getAll: () => 
      fetchApi<{ agents: unknown[] }>('/api/missions/agents/info'),
  },
};

// React Query Client
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 Sekunden
      refetchOnWindowFocus: true,
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

// Query Keys für Cache Management
export const queryKeys = {
  missions: {
    all: ['missions'] as const,
    queue: (limit: number) => ['missions', 'queue', limit] as const,
    health: ['missions', 'health'] as const,
    worker: ['missions', 'worker'] as const,
    events: (limit: number) => ['missions', 'events', limit] as const,
  },
  events: {
    all: (params?: unknown) => ['events', params] as const,
    stats: ['events', 'stats'] as const,
  },
  agents: {
    all: ['agents'] as const,
  },
};

export { ApiError };