import { betterAuth } from "better-auth"
import { nextCookies } from "better-auth/next-js"

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
    // Use memory adapter for simple dummy auth
    // In production, replace with PostgreSQL/SQLite adapter
    provider: "sqlite",
    url: ":memory:",
  },
  plugins: [nextCookies()],
  emailAndPassword: {
    enabled: true,
    autoSignIn: true,
    // Simple validation - in production use proper password hashing
    async verifyPassword(password: string, hash: string) {
      return password === hash
    },
    async hashPassword(password: string) {
      return password // Plain text for dummy auth
    },
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

// Helper to seed dummy users
export async function seedDummyUsers() {
  for (const user of DUMMY_USERS) {
    try {
      await auth.api.signUpEmail({
        body: {
          email: user.email,
          password: user.password,
          name: user.name,
        },
      })
      console.log(`Created user: ${user.email}`)
    } catch (e) {
      // User might already exist
      console.log(`User ${user.email} already exists or error:`, e)
    }
  }
}
