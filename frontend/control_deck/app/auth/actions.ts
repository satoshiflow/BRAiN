/**
 * BRAiN Authentication Server Actions
 * 
 * SECURITY:
 * - Server-side only execution
 * - POST-only via form actions
 * - CSRF protection through NextAuth
 * - Input validation with Zod (optional)
 * - No credentials in URL
 */

"use server";

import { signIn, signOut } from "@/auth";
import { AuthError } from "next-auth";
import { redirect } from "next/navigation";

// ============================================================================
// Types
// ============================================================================

export interface LoginResult {
  success: boolean;
  error?: string;
  callbackUrl?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
  callbackUrl?: string;
}

// ============================================================================
// Login Action
// ============================================================================

/**
 * Server Action for user login
 * 
 * SECURITY: This function only runs server-side
 * - Credentials are never exposed to client
 * - POST request enforced by Next.js Server Actions
 * - CSRF token validated by NextAuth
 * 
 * @param formData - Form data containing email and password
 * @returns LoginResult with success status
 */
export async function loginAction(formData: FormData): Promise<LoginResult> {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const callbackUrl = (formData.get("callbackUrl") as string) || "/dashboard";

  // Input validation
  if (!email || !password) {
    return {
      success: false,
      error: "Email and password are required",
    };
  }

  // Email format validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return {
      success: false,
      error: "Invalid email format",
    };
  }

  try {
    // Attempt to sign in with credentials
    const result = await signIn("credentials", {
      email,
      password,
      redirect: false, // Handle redirect manually
    });

    // Success - return success result (redirect handled by client)
    return {
      success: true,
      callbackUrl,
    };
  } catch (error) {
    // Handle AuthError from NextAuth
    if (error instanceof AuthError) {
      switch (error.type) {
        case "CredentialsSignin":
          return {
            success: false,
            error: "Invalid email or password",
          };
        case "CallbackRouteError":
          return {
            success: false,
            error: "Authentication error occurred",
          };
        default:
          return {
            success: false,
            error: "An error occurred during sign in",
          };
      }
    }

    // Log unexpected errors (don't expose details to client)
    console.error("[Auth] Unexpected error during login:", error);
    
    return {
      success: false,
      error: "An unexpected error occurred. Please try again.",
    };
  }
}

// ============================================================================
// Logout Action
// ============================================================================

/**
 * Server Action for user logout
 * 
 * SECURITY: 
 * - Clears session cookie (HttpOnly)
 * - Invalidates JWT token
 * - Redirects to sign-in page
 */
export async function logoutAction() {
  try {
    await signOut({ 
      redirectTo: "/auth/signin",
      redirect: true,
    });
  } catch (error) {
    if ((error as Error).message === "NEXT_REDIRECT") {
      throw error;
    }
    console.error("[Auth] Logout error:", error);
    redirect("/auth/signin");
  }
}

// ============================================================================
// Helper Functions - MOVED to lib/auth-helpers.ts
// ============================================================================
// Note: hasRequiredRole and canAccessAxe are now in lib/auth-helpers.ts
// to avoid Server Action restrictions
