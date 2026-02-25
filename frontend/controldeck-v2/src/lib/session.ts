// DEPRECATED: Use @/lib/auth.ts (Better Auth) instead
// This file is kept for compatibility but all functions are no-ops
// Better Auth handles sessions via PostgreSQL

export function generateSessionId(): string {
  throw new Error("DEPRECATED: Use Better Auth from @/lib/auth.ts");
}

export async function createSession(userId: string, rememberMe?: boolean): Promise<string> {
  throw new Error("DEPRECATED: Use Better Auth from @/lib/auth.ts");
}

export async function getSession(): Promise<null> {
  return null;
}

export async function requireUser(): Promise<never> {
  throw new Error("DEPRECATED: Use Better Auth from @/lib/auth.ts");
}

export async function destroySession(): Promise<void> {
  // No-op
}
