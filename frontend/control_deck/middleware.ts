/**
 * BRAiN Authentication Middleware
 * 
 * SECURITY:
 * - Protects all routes except public ones
 * - Role-based access control
 * - AXE UI protection (admin/operator only)
 * - Admin-only user management
 * - Redirects unauthenticated users to sign-in
 */

import { auth } from "@/auth";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// =============================================================================
// Route Definitions
// =============================================================================

const PUBLIC_ROUTES = [
  "/",
  "/auth/signin",
  "/auth/signout",
  "/auth/error",
  "/api/auth",
  "/_next",
  "/favicon.ico",
  "/public",
];

// Routes requiring authentication
const PROTECTED_ROUTES = [
  "/dashboard",
  "/agents",
  "/missions",
  "/activity",
  "/settings",
  "/system",
];

// AXE UI routes (admin and operator only)
const AXE_ROUTES = [
  "/axe",
  "/control-deck/axe",
];

// Admin-only routes
const ADMIN_ROUTES = [
  "/admin",
  "/api/admin",
  "/settings/users",
  "/system/config",
];

// API routes that require authentication
const PROTECTED_API_ROUTES = [
  "/api/admin",
  "/api/agents",
  "/api/missions",
];

// =============================================================================
// Helper Functions
// =============================================================================

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => 
    pathname === route || pathname.startsWith(route + "/")
  );
}

function isAxeRoute(pathname: string): boolean {
  return AXE_ROUTES.some(route => 
    pathname === route || pathname.startsWith(route + "/")
  );
}

function isAdminRoute(pathname: string): boolean {
  return ADMIN_ROUTES.some(route =>
    pathname === route || pathname.startsWith(route + "/")
  );
}

function isProtectedApiRoute(pathname: string): boolean {
  return PROTECTED_API_ROUTES.some(route =>
    pathname.startsWith(route)
  );
}

function canAccessAxe(role?: string): boolean {
  return role === "admin" || role === "operator";
}

function isAdmin(role?: string): boolean {
  return role === "admin";
}

// =============================================================================
// Middleware
// =============================================================================

export default auth((req) => {
  const { nextUrl } = req;
  const { pathname } = nextUrl;
  const session = req.auth;
  const isLoggedIn = !!session?.user;
  const userRole = session?.user?.role;

  // Allow Next.js internal routes
  if (pathname.startsWith("/_next") || 
      pathname.startsWith("/api/auth") ||
      pathname === "/favicon.ico") {
    return NextResponse.next();
  }

  // Check if it's a public route
  if (isPublicRoute(pathname)) {
    // Redirect authenticated users away from sign-in page
    if (isLoggedIn && pathname === "/auth/signin") {
      const callbackUrl = nextUrl.searchParams.get("callbackUrl");
      return NextResponse.redirect(new URL(callbackUrl || "/dashboard", nextUrl));
    }
    return NextResponse.next();
  }

  // Check authentication for all other routes
  if (!isLoggedIn) {
    const signInUrl = new URL("/auth/signin", nextUrl);
    signInUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(signInUrl);
  }

  // Check admin-only routes
  if (isAdminRoute(pathname) && !isAdmin(userRole)) {
    console.warn(`[Auth] Access denied to ${pathname}: User ${session.user?.email} is not admin`);
    return NextResponse.redirect(new URL("/dashboard?error=insufficient_permissions", nextUrl));
  }

  // Check AXE UI access (admin and operator only)
  if (isAxeRoute(pathname) && !canAccessAxe(userRole)) {
    console.warn(`[Auth] AXE access denied: User ${session.user?.email} has role ${userRole}`);
    return NextResponse.redirect(new URL("/dashboard?error=axe_access_denied", nextUrl));
  }

  // Add security headers to response
  const response = NextResponse.next();
  
  // Prevent clickjacking
  response.headers.set("X-Frame-Options", "DENY");
  
  // Prevent MIME type sniffing
  response.headers.set("X-Content-Type-Options", "nosniff");
  
  // XSS Protection
  response.headers.set("X-XSS-Protection", "1; mode=block");
  
  // Referrer Policy
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  
  // Permissions Policy
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), interest-cohort=()"
  );

  return response;
});

// =============================================================================
// Matcher Config
// =============================================================================

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|public/).*)",
  ],
};
