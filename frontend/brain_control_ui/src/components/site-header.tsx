"use client";

import { usePathname } from "next/navigation";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-toggle";

const TITLES: Record<
  string,
  {
    title: string;
    subtitle?: string;
  }
> = {
  "/": {
    title: "BRAiN Control Center",
    subtitle: "Overview · Cluster · Missions · Agents",
  },
  "/agents": {
    title: "Agents Deck",
    subtitle: "Agentenstatus, Details & Commands",
  },
  "/missions": {
    title: "Missions Deck",
    subtitle: "Queue, Status & Mission Flow",
  },
  "/settings": {
    title: "Settings",
    subtitle: "Systemweite BRAiN-Konfiguration",
  },
  "/settings/llm": {
    title: "LLM Config",
    subtitle: "Provider, Host, Model & Limits",
  },
  "/settings/agents": {
    title: "Agent Config",
    subtitle: "Agenten-Profile & Lifecycle",
  },
};

export function SiteHeader() {
  const pathname = usePathname();
  const cfg =
    TITLES[pathname] ??
    ({
      title: "BRAiN Control Deck",
      subtitle: "Cluster · Missions · Agents",
    } as const);

  return (
    <header className="flex h-[var(--header-height,3.5rem)] shrink-0 items-center gap-2 border-b border-border bg-background/90 backdrop-blur-xl transition-[width,height] ease-linear">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-6 data-[orientation=vertical]:h-6"
        />
        <div className="flex flex-col">
          <h1 className="text-sm font-semibold uppercase tracking-[0.24em]">
            {cfg.title}
          </h1>
          {cfg.subtitle && (
            <p className="text-[0.7rem] text-muted-foreground">
              {cfg.subtitle}
            </p>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="hidden sm:inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-[2px] text-[0.65rem] uppercase tracking-[0.16em] text-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" />
            System Online
          </span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
