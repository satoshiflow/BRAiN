/**
 * ⚠️ DEPRECATED - DO NOT USE FOR PRODUCTION AUTH
 * 
 * This module uses IN-MEMORY session storage which:
 * - Loses all sessions on server restart
 * - Doesn't work with multiple server instances
 * - Is NOT the single source of truth
 * 
 * USE INSTEAD: auth-server.ts
 * - Validates against Better Auth service (PostgreSQL)
 * - Single source of truth for authentication
 * - Proper session persistence
 * 
 * This file is kept for reference only.
 * @deprecated Use auth-server.ts for all auth operations
 */

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import crypto from 'crypto';

// Session configuration
const SESSION_COOKIE_NAME = 'session_id';
const SESSION_TTL_HOURS = 24; // Default: 24 hours
const SESSION_TTL_REMEMBER_ME_DAYS = 7; // 7 days for "remember me"

export interface Session {
  id: string;
  userId: string;
  expiresAt: Date;
  createdAt: Date;
}

// In-memory session store (replace with Redis/DB in production)
const sessionStore = new Map<string, Session>();

/**
 * Generate a cryptographically secure session ID
 * Uses crypto.randomUUID() - NOT Math.random()
 */
export function generateSessionId(): string {
  return crypto.randomUUID();
}

/**
 * Calculate session expiration date
 */
export function getSessionExpiry(rememberMe = false): Date {
  const now = new Date();
  if (rememberMe) {
    return new Date(now.getTime() + SESSION_TTL_REMEMBER_ME_DAYS * 24 * 60 * 60 * 1000);
  }
  return new Date(now.getTime() + SESSION_TTL_HOURS * 60 * 60 * 1000);
}

/**
 * Create a new session for a user
 */
export async function createSession(
  userId: string, 
  rememberMe = false
): Promise<string> {
  const sessionId = generateSessionId();
  const expiresAt = getSessionExpiry(rememberMe);
  
  const session: Session = {
    id: sessionId,
    userId,
    expiresAt,
    createdAt: new Date(),
  };
  
  // Store session
  sessionStore.set(sessionId, session);
  
  // Set secure cookie
  const cookieStore = await cookies();
  cookieStore.set({
    name: SESSION_COOKIE_NAME,
    value: sessionId,
    httpOnly: true,                          // Prevent XSS access
    secure: process.env.NODE_ENV === 'production', // HTTPS only in prod
    sameSite: 'strict',                      // CSRF protection
    expires: expiresAt,
    path: '/',
  });
  
  return sessionId;
}

/**
 * Get current session from cookie
 */
export async function getSession(): Promise<Session | null> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  
  if (!sessionId) {
    return null;
  }
  
  const session = sessionStore.get(sessionId);
  
  if (!session) {
    return null;
  }
  
  // Check if session expired
  if (new Date() > session.expiresAt) {
    await destroySession();
    return null;
  }
  
  return session;
}

/**
 * Check if user is authenticated
 * Redirects to /auth/login if not authenticated
 */
export async function requireUser(): Promise<{ userId: string }> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  
  if (!sessionId) {
    redirect("/auth/login");
  }
  
  const session = sessionStore.get(sessionId);
  
  if (!session) {
    redirect("/auth/login");
  }
  
  // Check if session expired
  if (new Date() > session.expiresAt) {
    await destroySession();
    redirect("/auth/login");
  }
  
  return { userId: session.userId };
}

/**
 * Destroy current session (logout)
 */
export async function destroySession(): Promise<void> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  
  if (sessionId) {
    sessionStore.delete(sessionId);
  }
  
  cookieStore.delete(SESSION_COOKIE_NAME);
}

/**
 * Refresh session expiration (extend on activity)
 */
export async function refreshSession(): Promise<void> {
  const session = await getSession();
  
  if (session) {
    const newExpiry = getSessionExpiry();
    session.expiresAt = newExpiry;
    sessionStore.set(session.id, session);
    
    // Update cookie expiry
    const cookieStore = await cookies();
    cookieStore.set({
      name: SESSION_COOKIE_NAME,
      value: session.id,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      expires: newExpiry,
      path: '/',
    });
  }
}

/**
 * Cleanup expired sessions (call periodically)
 */
export function cleanupExpiredSessions(): number {
  const now = new Date();
  let cleaned = 0;
  
  for (const [id, session] of sessionStore.entries()) {
    if (now > session.expiresAt) {
      sessionStore.delete(id);
      cleaned++;
    }
  }
  
  return cleaned;
}

export { SESSION_COOKIE_NAME, SESSION_TTL_HOURS, SESSION_TTL_REMEMBER_ME_DAYS };
