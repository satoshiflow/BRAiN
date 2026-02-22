import { createAuthClient } from "better-auth/react"
import { nextCookies } from "better-auth/next-js"

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL || "https://control.brain.falklabs.de",
  plugins: [nextCookies()],
})

export const { signIn, signOut, signUp, useSession } = authClient
