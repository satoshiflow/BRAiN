"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  LayoutDashboard,
  Network,
  Settings,
  Sparkles,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/components/ui/sidebar";

interface AppSidebarProps {
  variant?: "inset" | "floating";
}

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  badge?: string;
};

const mainNav: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/missions", label: "Missions", icon: Network },
];

const deckNav: NavItem[] = [
  { href: "/settings/llm", label: "LLM Config", icon: Sparkles },
  { href: "/settings/agents", label: "Agent Config", icon: Activity },
  { href: "/lifecycle", label: "Lifecycle", icon: Workflow, badge: "beta" },
  { href: "/supervisor", label: "Supervisor", icon: Settings, badge: "beta" },
];

export function AppSidebar({ variant = "inset" }: AppSidebarProps) {
  const pathname = usePathname();
  const { collapsed } = useSidebar();

  const widthClass = collapsed ? "w-[4.5rem]" : "w-64";

  return (
    <aside
      className={cn(
        "relative z-30 flex flex-col border-r border-border bg-background/95 backdrop-blur-xl",
        variant === "floating" &&
          "m-2 rounded-3xl border bg-background/90 shadow-xl",
        widthClass
      )}
    >
      {/* BRAND / CLUSTER BADGE */}
      <div className="flex flex-col gap-3 px-3 pt-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-amber-400 text-xs font-bold text-slate-900 shadow-lg">
            B
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-[0.7rem] font-semibold uppercase tracking-[0.32em] text-muted-foreground">
                F A L K
              </span>
              <span className="text-[0.7rem] text-muted-foreground">
                BRAiN Control Deck
              </span>
            </div>
          )}
        </div>

        {!collapsed && (
          <div className="rounded-2xl border border-border bg-muted/40 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                Cluster
              </span>
              <span className="flex items-center gap-1 text-[0.68rem] text-emerald-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" />
                Online
              </span>
            </div>
            <p className="mt-1 text-[0.65rem] text-muted-foreground">
              Local Dev · 0 kritische Incidents
            </p>
          </div>
        )}
      </div>

      <div className="mt-3 flex-1 overflow-y-auto px-2 pb-4">
        {/* MAIN NAV */}
        <nav className="mt-1 flex flex-col gap-1">
          {mainNav.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center gap-2 rounded-2xl px-2 py-1.5 text-[0.8rem] font-medium transition",
                  active
                    ? "bg-foreground text-background shadow-md"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                )}
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-background/70 text-[0.9rem]">
                  <Icon className="h-4 w-4" />
                </span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* DECKS */}
        <div className="mt-4 border-t border-border pt-3">
          {!collapsed && (
            <div className="mb-2 text-[0.68rem] uppercase tracking-[0.2em] text-muted-foreground">
              Decks
            </div>
          )}
          <nav className="flex flex-col gap-1">
            {deckNav.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "group flex items-center gap-2 rounded-2xl px-2 py-1.5 text-[0.78rem] font-medium transition",
                    active
                      ? "bg-foreground text-background shadow-md"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  )}
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-background/70 text-[0.9rem]">
                    <Icon className="h-4 w-4" />
                  </span>
                  {!collapsed && (
                    <span className="flex items-center gap-2">
                      {item.label}
                      {item.badge && (
                        <span className="rounded-full border border-border px-2 py-[1px] text-[0.6rem] uppercase tracking-[0.16em] text-muted-foreground">
                          {item.badge}
                        </span>
                      )}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* FOOTER / USER */}
      <div className="border-t border-border px-3 py-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-2xl bg-muted text-xs">
            OF
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-[0.75rem] font-medium">Olaf Falk</span>
              <span className="text-[0.65rem] text-muted-foreground">
                Admin · Dev Cluster
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
