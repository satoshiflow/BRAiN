"use client";

import { createContext, useContext, useEffect, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useCurrentUser, isAuthenticated } from "@/hooks/useAuth";

interface AuthContextValue {
  isAuthenticated: boolean;
  username: string | null;
  isAdmin: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextValue>({
  isAuthenticated: false,
  username: null,
  isAdmin: false,
  isLoading: true,
});

export function useAuth() {
  return useContext(AuthContext);
}

interface AuthProviderProps {
  children: ReactNode;
  requireAuth?: boolean;
}

export function AuthProvider({ children, requireAuth = false }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: user, isLoading } = useCurrentUser();

  const authenticated = isAuthenticated();

  useEffect(() => {
    // Redirect to login if auth is required but user is not authenticated
    if (requireAuth && !isLoading && !authenticated && pathname !== "/login") {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [requireAuth, isLoading, authenticated, pathname, router]);

  const value: AuthContextValue = {
    isAuthenticated: authenticated,
    username: user?.username || null,
    isAdmin: user?.is_admin || false,
    isLoading,
  };

  // Show loading state while checking auth
  if (requireAuth && isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render protected content if not authenticated
  if (requireAuth && !authenticated && !isLoading) {
    return null;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
