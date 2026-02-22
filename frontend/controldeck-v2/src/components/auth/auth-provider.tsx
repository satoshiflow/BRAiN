"use client"

import { createContext, useContext, ReactNode, useState, useEffect } from "react"

/**
 * AUTH CONTEXT
 * 
 * Provides auth state to React components.
 * Uses /api/auth endpoint which stores sessions in SQLite.
 * 
 * KI Note: To add fields to user, update:
 * 1. This User interface
 * 2. lib/auth.ts Session type
 * 3. api/auth/route.ts GET response
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshSession = async () => {
    try {
      const res = await fetch("/api/auth", {
        credentials: "include",
        cache: "no-store",
      })
      
      if (res.ok) {
        const data = await res.json()
        if (data.user) {
          setUser(data.user)
        } else {
          setUser(null)
        }
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
