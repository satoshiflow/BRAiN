"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { ApiHealthIndicator } from "@/components/ApiHealthIndicator";
import { Tooltip } from "@/components/ui/tooltip";
import { getApiBase, getControlDeckBase } from "@/lib/config";

const navItems = [
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export function Navigation() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Mobile: Hamburger Menu Button (Fixed Position) */}
      <button
        onClick={() => setMobileMenuOpen(true)}
        className="fixed left-4 z-50 rounded-xl border border-cyan-400/40 bg-slate-950/85 p-3 text-cyan-100 shadow-[0_12px_28px_rgba(0,0,0,0.55)] backdrop-blur-md transition-colors hover:bg-slate-900 lg:hidden"
        style={{ top: "max(1rem, env(safe-area-inset-top))" }}
        aria-label="Open menu"
      >
        <Menu className="h-6 w-6" />
      </button>

      {/* Mobile: Sheet Sidebar */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-64 p-0 axe-panel border-slate-700/70">
          <NavigationContent
            pathname={pathname}
            onNavigate={() => setMobileMenuOpen(false)}
          />
        </SheetContent>
      </Sheet>

      {/* Desktop: Always Visible Sidebar */}
      <nav className="hidden lg:flex w-[18.5rem] axe-panel border-r border-cyan-500/15 flex-col sticky top-0 h-screen">
        <NavigationContent pathname={pathname} />
      </nav>
    </>
  );
}

function NavigationContent({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  const apiBase = getApiBase();
  const controlDeckAgentsUrl = `${getControlDeckBase()}/agents`;

  return (
    <>
      {/* Header */}
      <div className="border-b border-cyan-500/15 px-6 py-5">
        <div className="mb-2 inline-flex items-center rounded-full border border-amber-300/30 bg-amber-300/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] text-amber-200">
          AXE relay interface
        </div>
        <h1 className="axe-surface-title text-xl font-bold text-white">BRAiN AXE</h1>
        <p className="mt-1 text-xs text-slate-400">Auxiliary Execution Engine / Mission Surface</p>
        <ApiHealthIndicator />
      </div>

      {/* Navigation Links */}
      <div className="flex-1 space-y-2 overflow-y-auto p-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`group flex min-h-[44px] items-center gap-3 rounded-lg px-4 py-3 transition-all ${
                isActive
                  ? "border border-cyan-400/45 bg-cyan-500/15 text-cyan-100 shadow-[0_0_0_1px_rgba(34,211,238,0.18)]"
                  : "border border-transparent text-slate-300 hover:border-cyan-400/20 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <span className="text-lg transition-transform group-hover:scale-110">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div className="border-t border-cyan-500/15 p-4">
        <a
          href={controlDeckAgentsUrl}
          target="_blank"
          rel="noreferrer"
          className="mb-3 flex items-center gap-2 rounded-lg border border-amber-400/30 bg-orange-500/10 px-3 py-2 text-sm text-amber-100 transition-colors hover:border-amber-300/50 hover:bg-orange-500/20"
          onClick={onNavigate}
        >
          <span className="text-base">🧭</span>
          <span>ControlDeck Agents Relay</span>
        </a>
        <Tooltip content={<span>{apiBase}</span>}>
          <button type="button" className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300">
            <span className="truncate max-w-[190px]">{apiBase}</span>
          </button>
        </Tooltip>
      </div>
    </>
  );
}
