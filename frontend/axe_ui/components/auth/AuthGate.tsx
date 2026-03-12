"use client";

import { LoginForm } from "@/components/auth/LoginForm";
import { useAuthSession } from "@/hooks/useAuthSession";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status, login } = useAuthSession();

  if (status === "authenticated") {
    return <>{children}</>;
  }

  return <LoginForm onSubmit={login} loading={status === "loading"} />;
}
