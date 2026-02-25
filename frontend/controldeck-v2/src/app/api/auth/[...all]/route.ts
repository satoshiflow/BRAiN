import { auth } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";

// Handle all auth routes
export async function GET(request: NextRequest) {
  return auth.handler(request);
}

export async function POST(request: NextRequest) {
  return auth.handler(request);
}
