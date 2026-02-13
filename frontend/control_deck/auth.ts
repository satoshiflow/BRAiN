import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

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
  providers: [
    CredentialsProvider({
      id: "credentials",
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        // Demo-Authentifizierung
        if (credentials?.password === "brain") {
          return {
            id: "demo-user-1",
            email: String(credentials.email || "admin@brain.local"),
            name: "Demo Admin",
            role: "admin",
            groups: ["admin", "operator"],
          };
        }
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
