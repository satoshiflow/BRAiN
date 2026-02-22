"use client"

import { createContext, useContext, ReactNode } from "react"
import { useSession } from "@/lib/auth-client"

type User = {
  id: string
  email: string
  name: string
  role: string
}

type AuthContextType = {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: session, isPending } = useSession()

  const user = session?.user
    ? {
        id: session.user.id,
        email: session.user.email,
        name: session.user.name || session.user.email,
        role: (session.user as any).role || "agent",
      }
    : null

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading: isPending,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
