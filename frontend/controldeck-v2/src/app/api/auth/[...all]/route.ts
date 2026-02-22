import { auth } from "@/lib/auth"
import { NextRequest } from "next/server"
import { mkdirSync, existsSync } from "fs"
import { join } from "path"

// Ensure data directory exists
const dataDir = join(process.cwd(), "data")
if (!existsSync(dataDir)) {
  mkdirSync(dataDir, { recursive: true })
}

// Handle all auth routes: /api/auth/*
export async function GET(request: NextRequest) {
  return auth.handler(request)
}

export async function POST(request: NextRequest) {
  return auth.handler(request)
}
