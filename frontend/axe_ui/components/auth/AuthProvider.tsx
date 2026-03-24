"use client";

import { AuthSessionProvider } from "@/hooks/useAuthSession";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <AuthSessionProvider>{children}</AuthSessionProvider>;
}
