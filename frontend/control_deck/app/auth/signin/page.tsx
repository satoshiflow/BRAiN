/**
 * BRAiN Sign-In Page
 * 
 * SECURITY:
 * - Static generation with Server Action
 * - POST-only credential submission
 * - CSRF protection via NextAuth
 * - No client-side state for credentials
 * - Input validation
 */

import { Suspense } from "react";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { loginAction } from "../actions";
import { SignInForm } from "./signin-form";
import { Metadata } from "next";

// ============================================================================
// Metadata
// ============================================================================

export const metadata: Metadata = {
  title: "Sign In | BRAiN Control Deck",
  description: "Sign in to BRAiN Control Deck",
};

// ============================================================================
// Search Params Component
// ============================================================================

interface SignInPageProps {
  searchParams: Promise<{ 
    callbackUrl?: string; 
    error?: string;
  }>;
}

// ============================================================================
// Main Page Component
// ============================================================================

export default async function SignInPage({ searchParams }: SignInPageProps) {
  // Check if user is already authenticated
  const session = await auth();
  const params = await searchParams;
  
  if (session?.user) {
    // Already logged in, redirect to callback or dashboard
    redirect(params.callbackUrl || "/dashboard");
  }

  // Pre-bind the login action with callback URL
  const boundLoginAction = loginAction.bind(null);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-blue-950 to-gray-900">
      <div className="max-w-md w-full mx-4">
        {/* Card */}
        <div className="bg-gray-800/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700 p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full mx-auto mb-4 flex items-center justify-center shadow-lg shadow-blue-600/20">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">BRAiN</h1>
            <p className="text-gray-400">Control Deck</p>
          </div>

          {/* Error Display */}
          {params.error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-red-400 text-sm">
                  {params.error === "CredentialsSignin" && "Invalid email or password"}
                  {params.error === "OAuthSignin" && "Error signing in with provider"}
                  {params.error === "OAuthCallback" && "Error completing sign in"}
                  {params.error === "OAuthCreateAccount" && "Error creating account"}
                  {params.error === "EmailCreateAccount" && "Error creating account"}
                  {params.error === "Callback" && "Error in callback"}
                  {params.error === "OAuthAccountNotLinked" && "Account not linked"}
                  {params.error === "EmailSignin" && "Error sending email"}
                  {params.error === "CredentialsSignin" && "Invalid credentials"}
                  {params.error === "SessionRequired" && "Please sign in to access this page"}
                  {!params.error.startsWith("OAuth") && !params.error.startsWith("Credentials") && !params.error.startsWith("Session") && params.error}
                </p>
              </div>
            </div>
          )}

          {/* Credentials Form (Server Action) */}
          <Suspense fallback={
            <div className="space-y-4">
              <div className="h-10 bg-gray-700/50 rounded animate-pulse"></div>
              <div className="h-10 bg-gray-700/50 rounded animate-pulse"></div>
              <div className="h-12 bg-blue-600/50 rounded animate-pulse"></div>
            </div>
          }>
            <SignInForm 
              callbackUrl={params.callbackUrl} 
              loginAction={boundLoginAction}
            />
          </Suspense>

          {/* Footer */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              BRAiN Control Deck v2.0 • Constitutional AI Framework
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Secured by NextAuth.js
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Force static generation
export const dynamic = "force-static";
