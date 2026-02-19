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
    // ✅ redirect: true ermöglicht Session-Erstellung
    await signIn("credentials", {
      email,
      password,
      redirectTo: callbackUrl,
    });

    // Diese Zeile wird nie erreicht (signIn redirected bei Erfolg)
    return { success: true };

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

    // Handle Next.js redirect (expected behavior)
    if ((error as Error)?.message?.includes("NEXT_REDIRECT")) {
      throw error; // Let Next.js handle the redirect
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
