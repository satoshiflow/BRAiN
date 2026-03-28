"use client";

import { LoginGateway } from "@/components/auth/LoginGateway";
import { useAuthSession } from "@/hooks/useAuthSession";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status, login } = useAuthSession();

  if (status === "authenticated") {
    return <>{children}</>;
  }

  return <LoginGateway onLogin={login} loading={status === "loading"} />;
}
