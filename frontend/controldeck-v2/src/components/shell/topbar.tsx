"use client";

import * as React from "react";
import { cn } from "@ui-core/utils";
import { Button, Avatar, AvatarFallback, AvatarImage } from "@ui-core/components";
import { DropdownMenu, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel } from "@ui-core/components/dropdown-menu";
import { MobileNavButton } from "./sidebar";
import { Search, Bell, User, Settings, Shield, Key, LogOut } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";

interface TopbarProps {
  title: string;
  subtitle?: string;
  onMenuClick?: () => void;
  actions?: React.ReactNode;
  className?: string;
}

export function Topbar({
  title,
  subtitle,
  onMenuClick,
  actions,
  className,
}: TopbarProps) {
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();

  const handleSignOut = async () => {
    await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "signOut" }),
    });
    router.push("/auth/login");
    router.refresh();
  };

  const getUserInitials = (email: string) => {
    return email.split("@")[0].slice(0, 2).toUpperCase();
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case "admin":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      case "operator":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      default:
        return "bg-green-500/10 text-green-500 border-green-500/20";
    }
  };

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex items-center justify-between h-16 px-4 bg-background/80 backdrop-blur-sm border-b border-border",
        className
      )}
    >
      <div className="flex items-center gap-4">
        <MobileNavButton onClick={onMenuClick || (() => {})} />
        <div>
          <h1 className="text-lg font-semibold">{title}</h1>
          {subtitle && (
            <p className="text-sm text-muted-foreground hidden sm:block">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Search */}
        <Button variant="ghost" size="icon" className="hidden sm:flex">
          <Search className="h-5 w-5" />
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-2 w-2 bg-primary rounded-full" />
        </Button>

        {/* Account Menu */}
        {isAuthenticated && user && (
          <DropdownMenu
            align="right"
            trigger={
              <Button
                variant="ghost"
                className="flex items-center gap-2 px-2 hover:bg-accent"
              >
                <Avatar className="h-8 w-8 border-2 border-border">
                  <AvatarImage src="" alt={user.email} />
                  <AvatarFallback className={cn("text-xs font-semibold", getRoleColor(user.role))}>
                    {getUserInitials(user.email)}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden md:flex flex-col items-start">
                  <span className="text-sm font-medium leading-none capitalize">
                    {user.email.split("@")[0]}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {user.email}
                  </span>
                </div>
              </Button>
            }
          >
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            
            <DropdownMenuItem
              icon={<User className="w-4 h-4" />}
              href="/account"
            >
              Account
            </DropdownMenuItem>
            
            <DropdownMenuItem
              icon={<Settings className="w-4 h-4" />}
              href="/settings"
            >
              Settings
            </DropdownMenuItem>
            
            <DropdownMenuItem
              icon={<Shield className="w-4 h-4" />}
              href="/security"
            >
              Security
            </DropdownMenuItem>
            
            <DropdownMenuItem
              icon={<Key className="w-4 h-4" />}
              href="/api-keys"
            >
              API Keys
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            
            <DropdownMenuItem
              icon={<LogOut className="w-4 h-4" />}
              onClick={handleSignOut}
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              Sign Out
            </DropdownMenuItem>
          </DropdownMenu>
        )}

        {/* Custom Actions */}
        {actions}
      </div>
    </header>
  );
}
