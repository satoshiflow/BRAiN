/**
 * Protected Route Group Layout
 * 
 * ALL pages under (protected) require valid authentication.
 * This layout validates the session on every request.
 * 
 * SECURITY PRINCIPLE:
 * - Cookie existence alone is NOT sufficient
 * - Session tokens are validated against PostgreSQL via Better Auth
 * - Invalid/expired sessions result in immediate redirect to login
 */

import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

// Force Node.js runtime for full auth validation
export const runtime = "nodejs";

export default async function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Get session from Better Auth
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  // Redirect to login if no valid session
  if (!session) {
    redirect("/auth/login");
  }

  // Pass user context to children
  return (
    <>
      <script
        id="__USER_CONTEXT__"
        type="application/json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            id: session.user.id,
            email: session.user.email,
            name: session.user.name,
            role: session.user.role,
          }),
        }}
      />
      {children}
    </>
  );
}
