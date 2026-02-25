import { NextRequest, NextResponse } from 'next/server';
import { login } from '@/lib/auth-server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, rememberMe } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required' },
        { status: 400 }
      );
    }

    const { userId, sessionId } = await login(email, password, rememberMe);

    return NextResponse.json(
      { 
        success: true, 
        userId,
        message: 'Login successful' 
      },
      { status: 200 }
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Login failed';
    return NextResponse.json(
      { error: message },
      { status: 401 }
    );
  }
}
