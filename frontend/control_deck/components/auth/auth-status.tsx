"use client";

import { useSession } from "next-auth/react";
import { LoginButton } from "./login-button";
import { UserInfo } from "./user-info";

interface AuthStatusProps {
  showLoginButton?: boolean;
}

export function AuthStatus({ showLoginButton = true }: AuthStatusProps) {
  const { status } = useSession();

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2">
        <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
      </div>
    );
  }

  if (status === "authenticated") {
    return <UserInfo />;
  }

  if (showLoginButton) {
    return <LoginButton />;
  }

  return null;
}
