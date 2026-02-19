import { NextResponse } from "next/server";
import { signOut } from "@/auth";

export async function POST() {
  try {
    await signOut({ redirectTo: "/auth/signin" });
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: "Sign out failed" },
      { status: 500 }
    );
  }
}
