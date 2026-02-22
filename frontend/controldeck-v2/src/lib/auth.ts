import { betterAuth } from "better-auth"
import { nextCookies } from "better-auth/next-js"

export const auth = betterAuth({
  database: {
    // Use file-based SQLite for persistence
    provider: "sqlite",
    url: process.env.BETTER_AUTH_DB_PATH || "./data/auth.db",
  },
  plugins: [nextCookies()],
  emailAndPassword: {
    enabled: true,
    autoSignIn: true,
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
  },
  user: {
    additionalFields: {
      role: {
        type: "string",
        required: true,
        defaultValue: "agent",
      },
    },
  },
  // Custom signup disabled - invitation only
  allowSignUp: false,
})
