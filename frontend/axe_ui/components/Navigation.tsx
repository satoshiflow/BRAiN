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
        className="fixed left-4 z-50 rounded-xl border border-sky-400/30 bg-slate-900/80 p-3 text-white shadow-xl backdrop-blur-md transition-colors hover:bg-slate-800 lg:hidden"
        style={{ top: "max(1rem, env(safe-area-inset-top))" }}
        aria-label="Open menu"
      >
        <Menu className="h-6 w-6" />
      </button>

      {/* Mobile: Sheet Sidebar */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-64 p-0 bg-slate-900 border-slate-800">
          <NavigationContent
            pathname={pathname}
            onNavigate={() => setMobileMenuOpen(false)}
          />
        </SheetContent>
      </Sheet>

      {/* Desktop: Always Visible Sidebar */}
      <nav className="hidden lg:flex w-64 bg-slate-900 border-r border-slate-800 flex-col sticky top-0 h-screen">
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
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold text-white">BRAiN AXE</h1>
        <p className="text-xs text-slate-400 mt-1">Auxiliary Execution Engine</p>
        <ApiHealthIndicator />
      </div>

      {/* Navigation Links */}
      <div className="flex-1 p-4 space-y-2 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors min-h-[44px] ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <a
          href={controlDeckAgentsUrl}
          target="_blank"
          rel="noreferrer"
          className="mb-3 flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 transition-colors hover:border-slate-600 hover:bg-slate-700"
          onClick={onNavigate}
        >
          <span className="text-base">🧭</span>
          <span>Agents im ControlDeck</span>
        </a>
        <Tooltip content={<span>{apiBase}</span>}>
          <button type="button" className="flex items-center gap-2 text-xs text-slate-500">
            <span className="truncate max-w-[190px]">{apiBase}</span>
          </button>
        </Tooltip>
      </div>
    </>
  );
}
