/**
 * BRAiN AUTH SYSTEM - SQLite Persistence Layer
 * 
 * Architecture:
 * - Simple session-based auth with SQLite persistence
 * - Survives container restarts (file-based)
 * - API compatible with future PostgreSQL migration
 * 
 * Database: /app/data/sessions.db (SQLite)
 * Table: sessions (id, user_email, user_role, data, expires_at, created_at)
 * 
 * Migration to PostgreSQL:
 * 1. Change connect() to use pg instead of better-sqlite3
 * 2. Update SQL syntax if needed (SQLite → PostgreSQL)
 * 3. Keep API identical - no frontend changes needed
 * 
 * See: docs/auth-architecture.md
 */

import Database from "better-sqlite3";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { NextRequest } from "next/server";
import { mkdirSync, existsSync } from "fs";
import { join } from "path";

// Ensure data directory exists
const DATA_DIR = process.env.AUTH_DATA_DIR || "./data";
if (!existsSync(DATA_DIR)) {
  mkdirSync(DATA_DIR, { recursive: true });
}

const DB_PATH = join(DATA_DIR, "sessions.db");

// Database connection (singleton)
let db: Database.Database | null = null;

function getDB(): Database.Database {
  if (!db) {
    db = new Database(DB_PATH);
    db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'agent',
        name TEXT,
        data TEXT,
        expires_at INTEGER NOT NULL,
        created_at INTEGER DEFAULT (unixepoch())
      );
      
      CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
      CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions(email);
    `);
    console.log(`[Auth] Database initialized at ${DB_PATH}`);
  }
  return db;
}

// Types
interface User {
  id: string;
  email: string;
  password: string;
  name: string;
  role: "admin" | "operator" | "agent";
}

interface Session {
  id: string;
  userId: string;
  email: string;
  role: string;
  name: string;
  expiresAt: Date;
}

// In-memory users (invitation-only system)
// TODO: Move to database for production
const DUMMY_USERS: Omit<User, "id">[] = [
  { email: "admin@brain.local", password: "admin", name: "Admin", role: "admin" },
  { email: "operator@brain.local", password: "operator", name: "Operator", role: "operator" },
  { email: "agent@brain.local", password: "agent", name: "Agent", role: "agent" },
  { email: "tester@brain.local", password: "tester", name: "Tester", role: "operator" },
];

const users = new Map<string, User>();
DUMMY_USERS.forEach((user, index) => {
  users.set(user.email, { ...user, id: `user-${index}` });
});

/**
 * Create new session for user
 */
export async function createSession(user: User): Promise<string> {
  const db = getDB();
  const sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000; // 7 days
  
  const stmt = db.prepare(`
    INSERT INTO sessions (id, user_id, email, role, name, expires_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  
  stmt.run(sessionId, user.id, user.email, user.role, user.name, expiresAt);
  
  return sessionId;
}

/**
 * Get session by ID
 */
export async function getSessionById(sessionId: string): Promise<Session | null> {
  const db = getDB();
  
  // Clean up expired sessions
  db.prepare("DELETE FROM sessions WHERE expires_at < ?").run(Date.now());
  
  const row = db.prepare(
    "SELECT * FROM sessions WHERE id = ? AND expires_at > ?"
  ).get(sessionId, Date.now()) as any;
  
  if (!row) return null;
  
  return {
    id: row.id,
    userId: row.user_id,
    email: row.email,
    role: row.role,
    name: row.name,
    expiresAt: new Date(row.expires_at),
  };
}

/**
 * Delete session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const db = getDB();
  db.prepare("DELETE FROM sessions WHERE id = ?").run(sessionId);
}

/**
 * Sign in user and create session
 */
export async function signIn(email: string, password: string): Promise<{ error?: string; sessionId?: string }> {
  const user = users.get(email);
  
  if (!user || user.password !== password) {
    return { error: "Invalid credentials" };
  }

  const sessionId = await createSession(user);
  
  // Set cookie
  const cookieStore = await cookies();
  cookieStore.set("session", sessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    path: "/",
  });
  
  return { sessionId };
}

/**
 * Sign out user
 */
export async function signOut(): Promise<void> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get("session")?.value;
  
  if (sessionId) {
    await deleteSession(sessionId);
    cookieStore.delete("session");
  }
}

/**
 * Get current session from cookie
 */
export async function getSession(): Promise<Session | null> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get("session")?.value;
  
  if (!sessionId) {
    return null;
  }
  
  return await getSessionById(sessionId);
}

/**
 * Get current user
 */
export async function getCurrentUser(): Promise<User | null> {
  const session = await getSession();
  if (!session) return null;
  
  return users.get(session.email) || null;
}

/**
 * Require auth middleware
 */
export async function requireAuth() {
  const session = await getSession();
  if (!session) {
    redirect("/auth/login");
  }
  return session;
}

/**
 * Middleware helper for Next.js
 */
export async function authMiddleware(request: NextRequest) {
  const sessionId = request.cookies.get("session")?.value;
  
  if (!sessionId) {
    return null;
  }
  
  return await getSessionById(sessionId);
}

export type { User, Session };
