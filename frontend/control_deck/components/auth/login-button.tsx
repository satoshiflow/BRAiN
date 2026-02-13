"use client";

import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";

interface LoginButtonProps {
  callbackUrl?: string;
  className?: string;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  showIcon?: boolean;
}

export function LoginButton({
  callbackUrl = "/",
  className,
  variant = "default",
  size = "default",
  showIcon = true,
}: LoginButtonProps) {
  return (
    <Button
      onClick={() => signIn("authentik", { callbackUrl })}
      variant={variant}
      size={size}
      className={className}
    >
      {showIcon && <LogIn className="mr-2 h-4 w-4" />}
      Anmelden
    </Button>
  );
}
