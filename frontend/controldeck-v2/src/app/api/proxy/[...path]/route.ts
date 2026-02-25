/**
 * API Proxy Route
 * 
 * Catches all /api/proxy/* requests and forwards them to the backend.
 * Benefits:
 * - Avoids CORS issues (same-origin)
 * - Automatically adds auth headers from session
 * - Server-side can use internal Docker networking
 * - Centralized error handling and logging
 */

import { NextRequest, NextResponse } from 'next/server';

/**
 * Get the internal backend URL from environment
 */
function getBackendUrl(): string {
  const url = process.env.BRAIN_API_BASE_INTERNAL;
  if (!url) {
    console.error('[Proxy] BRAIN_API_BASE_INTERNAL is not set!');
    throw new Error('Backend URL not configured');
  }
  return url.replace(/\/$/, ''); // Remove trailing slash
}

/**
 * Extract auth headers from the incoming request
 * Forwards session cookies or auth tokens to backend
 */
function extractAuthHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  
  // Forward Authorization header if present
  const authHeader = request.headers.get('authorization');
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }
  
  // Forward session cookie as X-Session-ID if present
  const sessionCookie = request.cookies.get('session');
  if (sessionCookie?.value) {
    headers['X-Session-ID'] = sessionCookie.value;
  }
  
  // Forward X-User-ID if present
  const userId = request.headers.get('x-user-id');
  if (userId) {
    headers['X-User-ID'] = userId;
  }
  
  return headers;
}

/**
 * Build the target backend URL from the request
 */
function buildTargetUrl(request: NextRequest): string {
  const backendBase = getBackendUrl();
  const path = request.nextUrl.pathname.replace('/api/proxy', '');
  const searchParams = request.nextUrl.search;
  
  return `${backendBase}${path}${searchParams}`;
}

/**
 * Handle the proxy request
 */
async function handleProxy(request: NextRequest): Promise<NextResponse> {
  const startTime = Date.now();
  
  try {
    const targetUrl = buildTargetUrl(request);
    const authHeaders = extractAuthHeaders(request);
    
    // Prepare headers
    const headers: Record<string, string> = {
      'Content-Type': request.headers.get('content-type') || 'application/json',
      'Accept': request.headers.get('accept') || 'application/json',
      ...authHeaders,
    };
    
    // Copy additional headers that should be forwarded
    const forwardHeaders = ['x-request-id', 'x-correlation-id'];
    for (const header of forwardHeaders) {
      const value = request.headers.get(header);
      if (value) {
        headers[header] = value;
      }
    }
    
    // Log the proxy request (dev mode)
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Proxy] ${request.method} ${targetUrl}`);
    }
    
    // Forward the request to backend
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.body ? await request.text() : undefined,
      // Important: Don't follow redirects, let the client handle them
      redirect: 'manual',
    });
    
    const duration = Date.now() - startTime;
    
    // Log response status
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Proxy] ${response.status} ${targetUrl} (${duration}ms)`);
    }
    
    // Create the response with the backend's body and status
    const responseBody = await response.text();
    const nextResponse = new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
    });
    
    // Copy response headers from backend
    response.headers.forEach((value, key) => {
      // Skip hop-by-hop headers
      if (!['transfer-encoding', 'connection', 'keep-alive'].includes(key.toLowerCase())) {
        nextResponse.headers.set(key, value);
      }
    });
    
    return nextResponse;
    
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`[Proxy] Error after ${duration}ms:`, error);
    
    return NextResponse.json(
      { 
        error: 'Proxy Error',
        message: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      },
      { status: 502 }
    );
  }
}

// Export handlers for all HTTP methods
export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const PATCH = handleProxy;
export const DELETE = handleProxy;
export const HEAD = handleProxy;
export const OPTIONS = handleProxy;
