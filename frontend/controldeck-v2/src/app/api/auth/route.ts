import { signIn, signOut, getSession } from "@/lib/auth"
import { NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const { action, email, password } = await request.json()
  
  if (action === "signIn") {
    const result = await signIn(email, password)
    
    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 401 })
    }
    
    return NextResponse.json({ success: true })
  }
  
  if (action === "signOut") {
    await signOut()
    return NextResponse.json({ success: true })
  }
  
  return NextResponse.json({ error: "Invalid action" }, { status: 400 })
}

export async function GET() {
  const session = await getSession()
  
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 })
  }
  
  return NextResponse.json({
    user: {
      id: session.userId,
      email: session.email,
      role: session.role,
    },
  })
}
