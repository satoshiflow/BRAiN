"use client";

import * as React from "react";
import { cn } from "@ui-core/utils";
import { Button } from "@ui-core/components";
import { MobileNavButton } from "./sidebar";
import { Search, Bell, User } from "lucide-react";

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

        {/* User Menu */}
        <Button variant="ghost" size="icon">
          <User className="h-5 w-5" />
        </Button>

        {/* Custom Actions */}
        {actions}
      </div>
    </header>
  );
}