import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Paths that don't require authentication
const PUBLIC_PATHS = ["/auth/login", "/auth/signup", "/api/auth"]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths
  if (PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  // Check for session cookie
  const sessionCookie = request.cookies.get("session")?.value
  
  if (!sessionCookie) {
    // Redirect to login if not authenticated
    const loginUrl = new URL("/auth/login", request.url)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

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
}
