/**
 * BRAiN Auth Error Page
 */

import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Authentication Error | BRAiN",
};

interface ErrorPageProps {
  searchParams: Promise<{ error?: string }>;
}

export default async function AuthErrorPage({ searchParams }: ErrorPageProps) {
  const params = await searchParams;
  
  const errorMessages: Record<string, string> = {
    Configuration: "There is a problem with the server configuration.",
    AccessDenied: "Access denied. You do not have permission to sign in.",
    Verification: "The verification token has expired or has already been used.",
    OAuthSignin: "Error in the OAuth sign-in process.",
    OAuthCallback: "Error in the OAuth callback process.",
    OAuthCreateAccount: "Could not create OAuth provider account.",
    EmailCreateAccount: "Could not create email provider account.",
    Callback: "Error in the OAuth callback handler.",
    OAuthAccountNotLinked: "Email already exists with different provider.",
    EmailSignin: "Error sending the email sign-in link.",
    CredentialsSignin: "Invalid email or password.",
    SessionRequired: "You must be signed in to access this page.",
    Default: "An unexpected authentication error occurred.",
  };

  const errorMessage = errorMessages[params.error || ""] || errorMessages.Default;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-red-950/30 to-gray-900">
      <div className="max-w-md w-full mx-4">
        <div className="bg-gray-800/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700 p-8">
          {/* Error Icon */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-red-600 rounded-full mx-auto mb-4 flex items-center justify-center">
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
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Authentication Error</h1>
            <p className="text-gray-400">{errorMessage}</p>
          </div>

          {/* Error Code (for debugging) */}
          {params.error && (
            <div className="mb-6 p-3 bg-gray-700/50 rounded-lg">
              <p className="text-xs text-gray-500 text-center font-mono">
                Error: {params.error}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="space-y-3">
            <Link
              href="/auth/signin"
              className="block w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors text-center"
            >
              Try Again
            </Link>
            <Link
              href="/"
              className="block w-full py-3 px-4 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors text-center"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export const dynamic = "force-static";
