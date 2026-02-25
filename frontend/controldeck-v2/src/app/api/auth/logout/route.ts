import { NextRequest, NextResponse } from 'next/server';
import { logout } from '@/lib/auth-server';

export async function POST(request: NextRequest) {
  try {
    await logout();

    return NextResponse.json(
      { 
        success: true, 
        message: 'Logout successful' 
      },
      { status: 200 }
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Logout failed';
    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
}
