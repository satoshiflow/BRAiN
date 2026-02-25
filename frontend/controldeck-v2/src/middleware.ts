/**
 * Next.js Middleware
 * 
 * IMPORTANT SECURITY NOTE:
 * This middleware ONLY handles path-based redirects and routing logic.
 * It does NOT perform authentication validation.
 * 
 * Why? Because:
 * 1. Middleware runs in Edge Runtime which has limited access to Node.js APIs
 * 2. Middleware cannot access the full database for session validation
 * 3. Cookie existence alone is NOT sufficient for authentication
 * 
 * REAL AUTHENTICATION happens in:
 * - src/lib/auth-server.ts (requireUser, getSession)
 * - src/app/(protected)/layout.tsx (server-side validation)
 * 
 * These use Node.js runtime and validate session tokens against the
 * Better Auth service database - the SINGLE SOURCE OF TRUTH.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Paths that are always public (no auth needed)
const PUBLIC_PATHS = [
  "/",
  "/auth/login",
  "/auth/register",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/api/auth", // Better Auth API routes
];

// Paths that are protected (require auth)
// These are handled by the (protected) route group layout
// which performs REAL session validation
const PROTECTED_PATH_PREFIXES = [
  "/dashboard",
  "/missions",
  "/agents",
  "/events",
  "/health",
  "/settings",
  "/account",
  "/api-keys",
  "/intelligence",
];

// Static assets that should never be blocked
const STATIC_PATHS = [
  "/_next",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
];

/**
 * Check if a path is public
 */
function isPublicPath(path: string): boolean {
  // Check exact matches
  if (PUBLIC_PATHS.includes(path)) {
    return true;
  }

  // Check if it's a static asset
  if (STATIC_PATHS.some((staticPath) => path.startsWith(staticPath))) {
    return true;
  }

  // Check if it's an auth API route
  if (path.startsWith("/api/auth")) {
    return true;
  }

  return false;
}

/**
 * Check if a path is in the protected area
 */
function isProtectedPath(path: string): boolean {
  return PROTECTED_PATH_PREFIXES.some((prefix) => path.startsWith(prefix));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow static assets and public paths without any checks
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // For protected paths, the (protected) layout will handle auth validation
  // We don't validate auth here - just ensure the route exists
  if (isProtectedPath(pathname)) {
    // Let the request through - the page layout will validate auth
    return NextResponse.next();
  }

  // For all other paths, let them through (will 404 if not found)
  return NextResponse.next();
}

/**
 * Configure middleware matcher
 * 
 * This runs on all paths except static files.
 * Static files are handled automatically by Next.js.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
