import { cookies } from "next/headers"
import { redirect } from "next/navigation"
import { NextRequest } from "next/server"

// Simple in-memory session store (works in container, lost on restart)
const sessions = new Map<string, Session>()
const users = new Map<string, User>()

interface User {
  id: string
  email: string
  password: string
  name: string
  role: "admin" | "operator" | "agent"
}

interface Session {
  id: string
  userId: string
  email: string
  role: string
  expiresAt: Date
}

// Dummy users - invitation only system
const DUMMY_USERS: Omit<User, "id">[] = [
  { email: "admin@brain.local", password: "admin", name: "Admin", role: "admin" },
  { email: "operator@brain.local", password: "operator", name: "Operator", role: "operator" },
  { email: "agent@brain.local", password: "agent", name: "Agent", role: "agent" },
  { email: "tester@brain.local", password: "tester", name: "Tester", role: "operator" },
]

// Initialize users
DUMMY_USERS.forEach((user, index) => {
  users.set(user.email, { ...user, id: `user-${index}` })
})

export async function signIn(email: string, password: string) {
  const user = users.get(email)
  
  if (!user || user.password !== password) {
    return { error: "Invalid credentials" }
  }

  // Create session
  const sessionId = `sess-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days
  
  const session: Session = {
    id: sessionId,
    userId: user.id,
    email: user.email,
    role: user.role,
    expiresAt,
  }
  
  sessions.set(sessionId, session)
  
  // Set cookie
  const cookieStore = await cookies()
  cookieStore.set("session", sessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: expiresAt,
    path: "/",
  })
  
  return { success: true }
}

export async function signOut() {
  const cookieStore = await cookies()
  const sessionId = cookieStore.get("session")?.value
  
  if (sessionId) {
    sessions.delete(sessionId)
    cookieStore.delete("session")
  }
  
  return { success: true }
}

export async function getSession() {
  const cookieStore = await cookies()
  const sessionId = cookieStore.get("session")?.value
  
  if (!sessionId) {
    return null
  }
  
  const session = sessions.get(sessionId)
  
  if (!session || session.expiresAt < new Date()) {
    if (session) sessions.delete(sessionId)
    cookieStore.delete("session")
    return null
  }
  
  return session
}

export async function getCurrentUser() {
  const session = await getSession()
  if (!session) return null
  
  return users.get(session.email) || null
}

export async function requireAuth() {
  const session = await getSession()
  if (!session) {
    redirect("/auth/login")
  }
  return session
}

export async function authMiddleware(request: NextRequest) {
  const sessionId = request.cookies.get("session")?.value
  
  if (!sessionId) {
    return null
  }
  
  const session = sessions.get(sessionId)
  
  if (!session || session.expiresAt < new Date()) {
    if (session) sessions.delete(sessionId)
    return null
  }
  
  return session
}

export type { User, Session }
