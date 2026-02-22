import { auth } from "@/lib/auth"
import { NextRequest } from "next/server"

// Handle all auth routes: /api/auth/*
export async function GET(request: NextRequest) {
  return auth.handler(request)
}

export async function POST(request: NextRequest) {
  return auth.handler(request)
}
