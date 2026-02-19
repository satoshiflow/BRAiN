"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useState } from "react";
import {
  LayoutDashboard,
  Rocket,
  Bot,
  Shield,
  Settings,
  Play,
  History,
  ClipboardList,
  Puzzle,
  Users,
  Eye,
  Cpu,
  ShieldCheck,
  Activity,
  ChevronRight,
  ChevronDown,
  Bird,
  User,
  FileText,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: number;
}

interface NavGroup {
  label: string;
  icon: React.ElementType;
  items: NavItem[];
  defaultOpen?: boolean;
}

const navGroups: NavGroup[] = [
  {
    label: "Home",
    icon: LayoutDashboard,
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    ],
    defaultOpen: true,
  },
  {
    label: "Missions",
    icon: Rocket,
    items: [
      { label: "Active Missions", href: "/missions", icon: Play },
      { label: "Mission History", href: "/missions/history", icon: History },
      { label: "Templates", href: "/missions/templates", icon: ClipboardList },
    ],
  },
  {
    label: "Agents",
    icon: Bot,
    items: [
      { label: "Agent Registry", href: "/agents", icon: Users },
      { label: "Skills Library", href: "/agents/skills", icon: Puzzle },
      { label: "Supervisor", href: "/agents/supervisor", icon: Eye },
    ],
  },
  {
    label: "AXE Management",
    icon: Shield,
    items: [
      { label: "Identity", href: "/axe/identity", icon: User },
      { label: "Knowledge Docs", href: "/axe/knowledge", icon: FileText },
    ],
  },
  {
    label: "System",
    icon: Shield,
    items: [
      { label: "Core Modules", href: "/system/modules", icon: Cpu },
      { label: "Immune System", href: "/system/immune", icon: ShieldCheck },
      { label: "Activity Log", href: "/system/activity", icon: Activity },
    ],
  },
  {
    label: "Settings",
    icon: Settings,
    items: [
      { label: "General", href: "/settings/general", icon: Settings },
      { label: "Security", href: "/settings/security", icon: Shield },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [openGroups, setOpenGroups] = useState<string[]>(
    navGroups.filter(g => g.defaultOpen).map(g => g.label)
  );

  const toggleGroup = (label: string) => {
    setOpenGroups(prev => 
      prev.includes(label) 
        ? prev.filter(l => l !== label)
        : [...prev, label]
    );
  };

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border/50 bg-card/95 backdrop-blur-xl flex flex-col">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-border/50 px-6">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl falk-gradient shadow-lg shadow-falk-500/20">
            <Bird className="h-6 w-6 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold falk-gradient-text">FalkLabs</span>
            <span className="text-[10px] text-muted-foreground">BRAiN Control</span>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4">
        <div className="flex flex-col gap-2">
          {navGroups.map((group) => {
            const GroupIcon = group.icon;
            const isOpen = openGroups.includes(group.label);
            const isActive = group.items.some(item => 
              pathname === item.href || pathname.startsWith(`${item.href}/`)
            );

            return (
              <div key={group.label} className="flex flex-col">
                {/* Group Header */}
                <button
                  onClick={() => toggleGroup(group.label)}
                  className={cn(
                    "flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200",
                    isActive
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <GroupIcon className={cn(
                      "h-4 w-4 transition-colors",
                      isActive ? "text-primary" : "text-muted-foreground"
                    )} />
                    <span>{group.label}</span>
                  </div>
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>

                {/* Group Items */}
                {isOpen && (
                  <div className="ml-4 mt-1 flex flex-col gap-0.5 border-l border-border/50 pl-3">
                    {group.items.map((item) => {
                      const ItemIcon = item.icon;
                      const itemActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={cn(
                            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200",
                            itemActive
                              ? "bg-primary/10 text-primary font-medium"
                              : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                          )}
                        >
                          <ItemIcon className={cn(
                            "h-4 w-4",
                            itemActive ? "text-primary" : "text-muted-foreground"
                          )} />
                          <span>{item.label}</span>
                          {item.badge !== undefined && item.badge > 0 && (
                            <span className="ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary/20 px-1.5 text-[10px] font-medium text-primary">
                              {item.badge}
                            </span>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </nav>

      {/* Bottom Status */}
      <div className="border-t border-border/50 p-4">
        <div className="flex items-center gap-3 rounded-xl bg-secondary/50 p-3">
          <div className="status-dot online" />
          <div className="flex flex-col">
            <span className="text-xs font-medium text-foreground">System Online</span>
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-muted-foreground">v0.3.0</span>
              <span className="eu-badge">Sovereign AI</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
