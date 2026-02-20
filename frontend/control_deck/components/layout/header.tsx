"use client";

import { Bell, Search, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useState } from "react";
import dynamic from "next/dynamic";
import { Sidebar } from "./sidebar";

// TEMPORARY: Disabled AuthStatus to fix build errors
// const AuthStatus = dynamic(
//   () => import("@/components/auth").then((mod) => mod.AuthStatus),
//   { ssr: false }
// );
const AuthStatus = () => <div className="h-8 w-8 rounded-full bg-muted" />;

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-border/50 bg-card/95 backdrop-blur-xl">
      <div className="flex h-full items-center justify-between px-6">
        {/* Left: Mobile Menu & Search */}
        <div className="flex items-center gap-4">
          {/* Mobile Menu Sheet */}
          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden h-10 w-10"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <Sidebar onNavigate={() => setMobileMenuOpen(false)} />
            </SheetContent>
          </Sheet>

          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search missions, agents..."
              className="w-80 pl-10 bg-secondary/50 border-0 focus-visible:ring-primary/20"
            />
          </div>
        </div>

        {/* Right: Notifications & Profile */}
        <div className="flex items-center gap-3">
          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5 text-muted-foreground" />
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary animate-pulse" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>Notifications</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <div className="max-h-80 overflow-y-auto">
                <NotificationItem
                  title="Mission Completed"
                  description="Data sync mission finished successfully"
                  time="2 min ago"
                  type="success"
                />
                <NotificationItem
                  title="Warning"
                  description="High memory usage detected"
                  time="15 min ago"
                  type="warning"
                />
                <NotificationItem
                  title="System Update"
                  description="BRAiN Core v0.3.0 is running"
                  time="1 hour ago"
                  type="info"
                />
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Profile / Auth Status */}
          <AuthStatus />
        </div>
      </div>
    </header>
  );
}

function NotificationItem({
  title,
  description,
  time,
  type,
}: {
  title: string;
  description: string;
  time: string;
  type: "success" | "warning" | "info" | "error";
}) {
  const colors = {
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    info: "bg-blue-500",
    error: "bg-red-500",
  };

  return (
    <div className="flex gap-3 p-3 hover:bg-secondary/50 transition-colors cursor-pointer">
      <div className={`mt-1 h-2 w-2 rounded-full ${colors[type]} flex-shrink-0`} />
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-medium">{title}</span>
        <span className="text-xs text-muted-foreground">{description}</span>
        <span className="text-[10px] text-muted-foreground/60">{time}</span>
      </div>
    </div>
  );
}
