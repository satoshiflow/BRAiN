/**
 * Public Landing Page
 * 
 * This is the entry point for unauthenticated users.
 * Redirects to dashboard if already logged in.
 */

import { redirect } from "next/navigation";
import Link from "next/link";
import { isUserAuthenticated } from "@/lib/auth-server";
import { Button } from "@ui-core/components";

export const runtime = "nodejs";

export default async function LandingPage() {
  // If already authenticated, go to dashboard
  const isAuthenticated = await isUserAuthenticated();
  
  if (isAuthenticated) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight">
            BRAiN ControlDeck
          </h1>
          <p className="mt-2 text-muted-foreground">
            Enterprise Futuristic Control System
          </p>
        </div>

        <div className="space-y-4">
          <Link href="/auth/login" className="block w-full">
            <Button size="lg" className="w-full">
              Anmelden
            </Button>
          </Link>
          
          <p className="text-center text-sm text-muted-foreground">
            Geschützter Bereich. Nur autorisierte Benutzer.
          </p>
        </div>
      </div>
    </div>
  );
}
