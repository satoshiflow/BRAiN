import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, name } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required' },
        { status: 400 }
      );
    }

    // Delegate to Better Auth
    const response = await auth.api.signUpEmail({
      body: { email, password, name: name || email },
      headers: request.headers,
      asResponse: true,
    });

    return response;
  } catch (error) {
    console.error('[Auth] Signup error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 400 }
    );
  }
}
