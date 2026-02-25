"use client"

import { createContext, useContext, ReactNode, useState, useEffect } from "react"
import { createAuthClient } from "better-auth/client"

/**
 * AUTH CONTEXT
 * 
 * Provides auth state to React components.
 * Uses Better Auth client for session management.
 * 
 * KI Note: To add fields to user, update:
 * 1. This User interface
 * 2. lib/auth.ts Session type
 */

interface User {
  id: string
  email: string
  role: string
  name?: string
}

type AuthContextType = {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  refreshSession: async () => {},
})

// Fix C: Use Better Auth client instead of deprecated /api/auth endpoint
const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:3000",
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshSession = async () => {
    try {
      // Use Better Auth client instead of raw fetch to /api/auth
      const { data: session } = await authClient.getSession()
      
      if (session?.user) {
        setUser({
          id: session.user.id,
          email: session.user.email,
          role: (session.user as any).role || "user",
          name: session.user.name || undefined,
        })
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error("Auth check failed:", error)
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshSession()
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
