import { betterAuth } from "better-auth"
import { nextCookies } from "better-auth/next-js"
import Database from "better-sqlite3"

// Dummy users for invitation-only system
// Roles: admin | operator | agent
const DUMMY_USERS = [
  { email: "admin@brain.local", password: "admin", role: "admin", name: "Admin" },
  { email: "operator@brain.local", password: "operator", role: "operator", name: "Operator" },
  { email: "agent@brain.local", password: "agent", role: "agent", name: "Agent" },
  { email: "tester@brain.local", password: "tester", role: "operator", name: "Tester" },
]

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
