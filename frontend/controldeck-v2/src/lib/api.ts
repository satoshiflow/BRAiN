/**
 * BRAiN API Client
 * 
 * Handles both server-side and client-side API calls to the backend.
 * Server-side uses BRAIN_API_BASE_INTERNAL (direct container networking)
 * Client-side uses NEXT_PUBLIC_BRAIN_API_BASE (public endpoint)
 */

// Detect if we're running on the server
const isServer = typeof window === 'undefined';

/**
 * Get the appropriate base URL for API calls
 * Server: Uses internal Docker network (http://backend:8000)
 * Client: Uses public URL (https://api.brain.falklabs.de)
 */
export function getApiBaseUrl(): string {
  if (isServer) {
    // Server-side: use internal URL
    const internalUrl = process.env.BRAIN_API_BASE_INTERNAL;
    if (!internalUrl) {
      console.warn('[API] BRAIN_API_BASE_INTERNAL not set, falling back to localhost:8000');
      return 'http://localhost:8000';
    }
    return internalUrl;
  } else {
    // Client-side: use public URL
    const publicUrl = process.env.NEXT_PUBLIC_BRAIN_API_BASE;
    if (!publicUrl) {
      console.warn('[API] NEXT_PUBLIC_BRAIN_API_BASE not set, falling back to current origin');
      return '';
    }
    return publicUrl;
  }
}

/**
 * Get WebSocket base URL
 * Fix E: WebSocket Security - wss:// validation in production
 */
export function getWsBaseUrl(): string {
  if (isServer) {
    const url = process.env.BRAIN_WS_BASE_INTERNAL;
    if (!url) {
      console.warn('[WS] BRAIN_WS_BASE_INTERNAL not set');
      return 'ws://backend:8000/ws'; // OK internally (Docker network, no TLS needed)
    }
    return url;
  } else {
    const url = process.env.NEXT_PUBLIC_BRAIN_WS_BASE;
    if (!url) {
      // Browser: wss:// for HTTPS pages, ws:// for HTTP (dev)
      const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
      return `${proto}://${typeof window !== 'undefined' ? window.location.host : 'localhost'}/ws`;
    }
    // Env var must use wss:// in production
    if (process.env.NODE_ENV === 'production' && url.startsWith('ws://')) {
      throw new Error('NEXT_PUBLIC_BRAIN_WS_BASE must use wss:// in production');
    }
    return url;
  }
}

/**
 * Build full API URL from path
 * @param path - API path (e.g., '/missions' or 'missions')
 * @returns Full URL
 */
export function buildApiUrl(path: string): string {
  const base = getApiBaseUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

/**
 * Standard fetch options for backend API calls
 * Includes credentials and default headers
 */
export function getDefaultFetchOptions(): RequestInit {
  return {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  };
}

/**
 * Make an API call to the backend
 * Automatically handles server vs client environments
 * 
 * @param path - API path
 * @param options - Fetch options
 * @returns Promise with parsed JSON response
 */
export async function apiCall<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = buildApiUrl(path);
  const defaultOptions = getDefaultFetchOptions();
  
  const response = await fetch(url, {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`API Error ${response.status}: ${errorText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Use the local proxy route for internal API calls
 * This avoids CORS issues and handles auth headers automatically
 * 
 * @param path - Path after /api/proxy/ (e.g., 'missions')
 * @param options - Fetch options
 * @returns Promise with parsed JSON response
 */
export async function proxyCall<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  const url = `/api/proxy/${cleanPath}`;
  
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`Proxy Error ${response.status}: ${errorText}`);
  }

  return response.json() as Promise<T>;
}

// =============================================================================
// Typed API Endpoints
// =============================================================================

export interface Mission {
  id: string;
  name: string;
  type: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  priority: 'high' | 'medium' | 'low';
  progress: number;
  createdAt: string;
  agent: string | null;
}

export interface Agent {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy';
  capabilities: string[];
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  components: Record<string, { status: string; message?: string }>;
}

/**
 * Missions API
 */
export const missionsApi = {
  getAll: () => proxyCall<Mission[]>('missions'),
  getById: (id: string) => proxyCall<Mission>(`missions/${id}`),
  create: (data: Partial<Mission>) => proxyCall<Mission>('missions', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: Partial<Mission>) => proxyCall<Mission>(`missions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  delete: (id: string) => proxyCall<void>(`missions/${id}`, {
    method: 'DELETE',
  }),
};

/**
 * Agents API
 */
export const agentsApi = {
  getAll: () => proxyCall<Agent[]>('agents'),
  getById: (id: string) => proxyCall<Agent>(`agents/${id}`),
};

/**
 * Health API
 */
export const healthApi = {
  getStatus: () => proxyCall<SystemHealth>('health'),
};

/**
 * Learning API
 */
export interface LearningStats {
  total_metrics_recorded: number;
  total_strategies: number;
  active_strategies: number;
  total_experiments: number;
  running_experiments: number;
}

export const learningApi = {
  getStats: () => proxyCall<LearningStats>('modules/learning/stats'),
  getStrategies: (agentId: string) =>
    proxyCall<any>(`modules/learning/strategies/${agentId}`),
  listExperiments: (agentId?: string) =>
    proxyCall<any>('modules/learning/experiments', {
      method: 'GET',
      ...(agentId ? { body: JSON.stringify({ agent_id: agentId }) } : {}),
    }),
  getExperiment: (experimentId: string) =>
    proxyCall<any>(`modules/learning/experiments/${experimentId}`),
};

/**
 * Memory API
 */
export const memoryApi = {
  getInfo: () => proxyCall<any>('modules/memory/info'),
  getStats: () => proxyCall<any>('modules/memory/stats'),
  getMemory: (id: string) => proxyCall<any>(`modules/memory/entries/${id}`),
  storeMemory: (data: any) =>
    proxyCall<any>('modules/memory/store', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getSessions: () => proxyCall<any>('modules/memory/sessions'),
};
