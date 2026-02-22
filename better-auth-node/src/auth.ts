import { betterAuth } from "better-auth";
import Database from "better-sqlite3";

const trustedOrigins = process.env.TRUSTED_ORIGINS?.split(",") || [
  "https://control.brain.falklabs.de",
  "https://axe.brain.falklabs.de",
  "https://api.brain.falklabs.de",
  "http://localhost:3000"
];

// Initialize SQLite database
const db = new Database("./data/better-auth.db");

export const auth = betterAuth({
  database: {
    db: db,
    type: "sqlite",
  },
  
  // Social Providers (optional)
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID || "",
      clientSecret: process.env.GITHUB_CLIENT_SECRET || "",
    },
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    },
  },
  
  // CORS Configuration
  trustedOrigins: trustedOrigins,
  
  // Advanced Cookie Settings
  advanced: {
    cookiePrefix: "brain_auth",
    useSecureCookies: process.env.NODE_ENV === "production",
    sameSite: "lax",
  },
  
  // Email Verification
  emailVerification: {
    sendOnSignUp: false,
    autoSignInAfterVerification: true,
  },
  
  // Session Configuration
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
  },
  
  // Rate Limiting
  rateLimit: {
    window: 60, // 1 minute
    max: 100, // 100 requests per minute
  },
});

export type Auth = typeof auth;