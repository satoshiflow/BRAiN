import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

// User type für internen Gebrauch
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role?: string;
  groups?: string[];
  accessToken?: string;
  refreshToken?: string;
}

// Extend the User type to include custom fields
declare module "next-auth" {
  interface User {
    groups?: string[];
    role?: string;
    accessToken?: string;
    refreshToken?: string;
  }
  interface Session {
    user: User & {
      id?: string;
      groups?: string[];
      role?: string;
      accessToken?: string;
      refreshToken?: string;
    };
    error?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    role?: string;
    groups?: string[];
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpires?: number;
    error?: string;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

/**
 * Refreshes the access token using the refresh token
 * Follows the backend token refresh pattern
 */
async function refreshAccessToken(token: import("next-auth/jwt").JWT): Promise<import("next-auth/jwt").JWT> {
  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    });

    if (!response.ok) {
      console.error("[Auth] Token refresh failed:", response.status);
      return {
        ...token,
        error: "RefreshAccessTokenError",
      };
    }

    const data = await response.json();

    return {
      ...token,
      accessToken: data.access_token,
      accessTokenExpires: Date.now() + 15 * 60 * 1000, // 15 minutes
      refreshToken: data.refresh_token ?? token.refreshToken, // Use new refresh token if provided
    };
  } catch (error) {
    console.error("[Auth] Token refresh error:", error);
    return {
      ...token,
      error: "RefreshAccessTokenError",
    };
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  secret: process.env.AUTH_SECRET,
  providers: [
    CredentialsProvider({
      id: "credentials",
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(
        credentials: Record<string, unknown> | undefined
      ): Promise<AuthUser | null> {
        // Type-safe credential extraction
        if (!credentials || typeof credentials !== "object") {
          console.warn("[Auth] No credentials provided");
          return null;
        }

        const email = credentials.email;
        const password = credentials.password;

        // Validate types
        if (typeof password !== "string" || typeof email !== "string") {
          console.warn("[Auth] Invalid credential types");
          return null;
        }

        // Check if in demo mode
        const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
        const DEMO_PASSWORD = process.env.DEMO_PASSWORD || "brain";

        if (DEMO_MODE && password === DEMO_PASSWORD) {
          console.log(`[Auth] Demo login: ${email}`);
          return {
            id: "demo-user-1",
            email: email,
            name: "Demo Admin",
            role: "admin",
            groups: ["admin", "operator"],
          };
        }

        // PRODUCTION: Backend authentication
        try {
          const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });

          if (!response.ok) {
            console.warn(`[Auth] Backend login failed: ${response.status}`);
            return null;
          }

          const data = await response.json();

          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.full_name || data.user.username,
            role: data.user.role,
            groups: [data.user.role],
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          };
        } catch (error) {
          console.error("[Auth] Backend authentication error:", error);
          return null;
        }
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  cookies: {
    sessionToken: {
      name: process.env.NODE_ENV === "production" 
        ? "__Host-next-auth.session-token" 
        : "next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
    callbackUrl: {
      name: process.env.NODE_ENV === "production" 
        ? "__Host-next-auth.callback-url" 
        : "next-auth.callback-url",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
    csrfToken: {
      name: process.env.NODE_ENV === "production" 
        ? "__Host-next-auth.csrf-token" 
        : "next-auth.csrf-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/signin",
  },
  // CSRF ist jetzt AKTIVIERT (skipCSRFCheck entfernt!)
  trustHost: true,
  callbacks: {
    async jwt({ token, user, account }) {
      // Initial sign in - store tokens and expiration
      if (user) {
        token.sub = user.id;
        token.email = user.email;
        token.name = user.name;
        token.role = user.role;
        token.groups = user.groups;
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        // Set token expiration (15 minutes from now)
        token.accessTokenExpires = Date.now() + 15 * 60 * 1000;
      }

      // Return previous token if the access token has not expired yet
      if (token.accessTokenExpires && Date.now() < token.accessTokenExpires) {
        return token;
      }

      // Access token has expired, try to refresh it
      // Only refresh if we have a refresh token
      if (token.refreshToken) {
        return await refreshAccessToken(token);
      }

      return token;
    },
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.sub as string;
        session.user.email = token.email as string;
        session.user.name = token.name as string;
        session.user.role = token.role as string;
        session.user.groups = token.groups as string[];
        session.user.accessToken = token.accessToken as string;
        session.user.refreshToken = token.refreshToken as string;
      }
      // Pass through any token errors to the session
      if (token.error) {
        session.error = token.error;
      }
      return session;
    },
    async redirect({ url, baseUrl }) {
      // Erlaube nur relative URLs oder gleiche Domain
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      if (url.startsWith(baseUrl)) return url;
      return `${baseUrl}/dashboard`;
    },
  },
});

// Export refreshAccessToken for potential external use
export { refreshAccessToken };
