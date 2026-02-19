"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

const navItems = [
  { href: "/", label: "Home", icon: "🏠" },
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/agents", label: "Agents", icon: "🤖" },
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
        className="fixed top-4 left-4 z-50 lg:hidden bg-slate-800 hover:bg-slate-700 text-white p-3 rounded-lg border border-slate-700 transition-colors"
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
  return (
    <>
      {/* Header */}
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold text-white">BRAiN AXE</h1>
        <p className="text-xs text-slate-400 mt-1">Auxiliary Execution Engine</p>
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
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span className="text-xs text-slate-400">System Online</span>
        </div>
      </div>
    </>
  );
}
