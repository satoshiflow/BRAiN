import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// Fix A: Hardcoded Secret - CRITICAL
// Validate that BETTER_AUTH_SECRET is set, no fallback to known defaults
const secret = process.env.BETTER_AUTH_SECRET;
if (!secret) {
  throw new Error(
    "BETTER_AUTH_SECRET environment variable is required. " +
    "Set it to a random 32+ character string."
  );
}

export const auth = betterAuth({
  secret,
  database: prismaAdapter(prisma, {
    provider: "postgresql",
  }),
  emailAndPassword: {
    enabled: true,
    autoSignIn: true,
    // bcrypt is used by default for password hashing
  },
  session: {
    expiresIn: 60 * 60 * 2, // 2 hours (was 7 days) - Security Best Practice
    updateAge: 60 * 60 * 1, // 1 hour
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // 5 minutes
    },
  },
  cookies: {
    sessionToken: {
      name: "session",
      options: {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        path: "/",
      },
    },
  },
});

export type AuthSession = typeof auth.$Infer.Session;
