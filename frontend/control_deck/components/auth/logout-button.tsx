import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";

interface LogoutButtonProps {
  className?: string;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  showIcon?: boolean;
}

export function LogoutButton({
  className,
  variant = "outline",
  size = "default",
  showIcon = true,
}: LogoutButtonProps) {
  return (
    <Button
      asChild
      variant={variant}
      size={size}
      className={className}
    >
      <Link href="/auth/signout">
        {showIcon && <LogOut className="mr-2 h-4 w-4" />}
        Abmelden
      </Link>
    </Button>
  );
}
