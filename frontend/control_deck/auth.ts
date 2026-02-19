import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

// User type für internen Gebrauch
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role?: string;
  groups?: string[];
}

// Extend the User type to include custom fields
declare module "next-auth" {
  interface User {
    groups?: string[];
    role?: string;
  }
  interface Session {
    user: User & {
      id?: string;
      groups?: string[];
      role?: string;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    role?: string;
    groups?: string[];
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

        // Demo-Mode für falklabs.de Production Server
        // Passwort kann via DEMO_PASSWORD env var oder Fallback gesetzt werden
        const DEMO_PASSWORD = process.env.DEMO_PASSWORD || "brain";

        // Demo-Login: Einfacher Passwort-Check
        if (password === DEMO_PASSWORD) {
          console.log(`[Auth] Demo login successful: ${email}`);

          return {
            id: "demo-user-1",
            email: email,
            name: "Demo Admin",
            role: "admin",
            groups: ["admin", "operator"],
          };
        }

        // TODO: Implement real backend authentication
        // Uncomment when backend auth endpoint is ready:
        //
        // try {
        //   const response = await fetch(
        //     `${process.env.NEXT_PUBLIC_BRAIN_API_BASE}/api/auth/login`,
        //     {
        //       method: "POST",
        //       headers: { "Content-Type": "application/json" },
        //       body: JSON.stringify({
        //         email: credentials.email,
        //         password: credentials.password,
        //       }),
        //     }
        //   );
        //
        //   if (!response.ok) {
        //     return null;
        //   }
        //
        //   const user = await response.json();
        //   return user;
        // } catch (error) {
        //   console.error("[Auth] Backend authentication failed:", error);
        //   return null;
        // }

        // Fail-closed: Reject invalid credentials
        console.warn(`[Auth] Login failed for: ${email}`);
        return null;
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
    async jwt({ token, user }) {
      if (user) {
        token.sub = user.id;
        token.email = user.email;
        token.name = user.name;
        token.role = user.role;
        token.groups = user.groups;
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
