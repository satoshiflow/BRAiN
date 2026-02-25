import { NextRequest, NextResponse } from 'next/server';
import { signup } from '@/lib/auth-server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required' },
        { status: 400 }
      );
    }

    const { userId, sessionId } = await signup(email, password);

    return NextResponse.json(
      { 
        success: true, 
        userId,
        message: 'User created successfully' 
      },
      { status: 201 }
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Signup failed';
    return NextResponse.json(
      { error: message },
      { status: 400 }
    );
  }
}
