"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface UseAuthOptions {
  required?: boolean;
  redirectTo?: string;
}

export function useAuth(options: UseAuthOptions = {}) {
  const { required = false, redirectTo = "/auth/signin" } = options;
  const { data: session, status, update } = useSession();
  const router = useRouter();

  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated";

  useEffect(() => {
    if (required && !isLoading && !isAuthenticated) {
      router.push(`${redirectTo}?callbackUrl=${window.location.pathname}`);
    }
  }, [required, isLoading, isAuthenticated, redirectTo, router]);

  return {
    session,
    status,
    isLoading,
    isAuthenticated,
    user: session?.user,
    updateSession: update,
  };
}
