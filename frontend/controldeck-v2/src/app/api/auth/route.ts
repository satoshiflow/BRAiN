/**
 * AUTH API ROUTE
 * 
 * Endpoints:
 * - POST /api/auth { action: "signIn", email, password } → Login
 * - POST /api/auth { action: "signOut" } → Logout  
 * - GET /api/auth → Get current session
 * 
 * Session Storage: SQLite (/app/data/sessions.db)
 * Persistence: Survives container restarts
 * 
 * KI/AI Assistant Context:
 * - This is the entry point for authentication
 * - All auth logic is in @/lib/auth.ts
 * - Sessions are stored in SQLite, not memory
 * - For PostgreSQL migration, only lib/auth.ts needs changes
 */

import { signIn, signOut, getSession } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, email, password } = body;
    
    if (action === "signIn") {
      const result = await signIn(email, password);
      
      if (result.error) {
        return NextResponse.json({ error: result.error }, { status: 401 });
      }
      
      return NextResponse.json({ success: true, sessionId: result.sessionId });
    }
    
    if (action === "signOut") {
      await signOut();
      return NextResponse.json({ success: true });
    }
    
    return NextResponse.json({ error: "Invalid action" }, { status: 400 });
  } catch (error) {
    console.error("[Auth API Error]", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

export async function GET() {
  try {
    const session = await getSession();
    
    if (!session) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }
    
    return NextResponse.json({
      user: {
        id: session.userId,
        email: session.email,
        role: session.role,
        name: session.name,
      },
    });
  } catch (error) {
    console.error("[Auth API Error]", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
