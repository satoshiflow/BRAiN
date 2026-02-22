"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@ui-core/utils";
import { Button } from "@ui-core/components";
import {
  LayoutDashboard,
  Target,
  Radio,
  Settings,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  Activity,
  Bot,
  Layers,
  PanelRight,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  group?: string;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, group: "Overview" },
  { label: "Components", href: "/components", icon: Layers, group: "Overview" },
  { label: "Modals", href: "/modals", icon: PanelRight, group: "Overview" },
  { label: "Missions", href: "/missions", icon: Target, group: "Operations" },
  { label: "Agents", href: "/agents", icon: Bot, group: "Operations" },
  { label: "Events", href: "/events", icon: Radio, group: "Operations" },
  { label: "Health", href: "/health", icon: Activity, group: "System" },
  { label: "Settings", href: "/settings", icon: Settings, group: "System" },
];

interface SidebarProps {
  className?: string;
  collapsed?: boolean;
  onCollapse?: (collapsed: boolean) => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({
  className,
  collapsed = false,
  onCollapse,
  mobileOpen = false,
  onMobileClose,
}: SidebarProps) {
  const pathname = usePathname();

  // Group nav items
  const groupedItems = navItems.reduce((acc, item) => {
    const group = item.group || "Other";
    if (!acc[group]) acc[group] = [];
    acc[group].push(item);
    return acc;
  }, {} as Record<string, NavItem[]>);

  const NavContent = () => {
    const { user } = useAuth();
    const router = useRouter();
    
    const handleLogout = async () => {
      await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "signOut" }),
      })
      router.push("/auth/login")
      router.refresh()
    };
    
    return (
      <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {Object.entries(groupedItems).map(([group, items]) => (
          <div key={group}>
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {group}
              </h3>
            )}
            <ul className="space-y-1">
              {items.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                const Icon = item.icon;
                
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href as any}
                      data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        isActive
                          ? "bg-secondary text-foreground border-l-2 border-primary"
                          : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground",
                        collapsed && "justify-center px-2"
                      )}
                    >
                      <span onClick={onMobileClose} className="flex items-center gap-3 w-full">
                        <Icon className={cn("h-5 w-5 flex-shrink-0", isActive && "text-primary")} />
                        {!collapsed && <span>{item.label}</span>}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        
        {/* Logout Button */}
        {user && (
          <div className="pt-4 border-t border-border">
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                Account
              </h3>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive",
                collapsed && "justify-center px-2"
              )}
            >
              <LogOut className="h-5 w-5 flex-shrink-0" />
              {!collapsed && <span>Logout</span>}
            </Button>
          </div>
        )}
      </nav>
    );
  };

  return (
    <>
      {/* Mobile Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-background border-r border-border transform transition-transform duration-200 ease-in-out lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          className
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-border">
          <span className="text-lg font-bold text-primary">BRAiN</span>
          <Button variant="ghost" size="icon" onClick={onMobileClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <NavContent />
      </aside>

      {/* Desktop Sidebar */}
      <aside
        data-testid="sidebar-desktop"
        className={cn(
          "hidden lg:flex flex-col bg-background border-r border-border h-screen sticky top-0 transition-all duration-200",
          collapsed ? "w-16" : "w-64",
          className
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-border">
          {!collapsed && <span className="text-lg font-bold text-primary">BRAiN</span>}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onCollapse?.(!collapsed)}
            className={cn("ml-auto", collapsed && "mx-auto")}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
        <NavContent />
      </aside>
    </>
  );
}

export function MobileNavButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="ghost" size="icon" className="lg:hidden" onClick={onClick}>
      <Menu className="h-5 w-5" />
    </Button>
  );
}