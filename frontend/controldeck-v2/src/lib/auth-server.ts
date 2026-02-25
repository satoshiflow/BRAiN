/**
 * Server-side authentication utilities
 * DEPRECATED: Use @/lib/auth.ts (Better Auth) instead
 * 
 * This file now re-exports from Better Auth for compatibility.
 * All auth operations go through Better Auth + PostgreSQL.
 */

import { auth } from "./auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

/**
 * Require authenticated user
 * Uses Better Auth session validation via PostgreSQL
 */
export async function requireUser() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/auth/login");
  }

  return {
    userId: session.user.id,
    email: session.user.email,
    name: session.user.name,
  };
}

/**
 * Get current session
 */
export async function getSession() {
  return await auth.api.getSession({
    headers: await headers(),
  });
}

/**
 * Check if user is authenticated
 */
export async function isUserAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return session !== null;
}

/**
 * @deprecated Use auth from @/lib/auth.ts directly
 * This compatibility layer will be removed in future versions.
 */
export const authCompat = {
  requireUser,
  getSession,
  isUserAuthenticated,
};
